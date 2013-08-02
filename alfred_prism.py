#!/usr/bin/env python
# coding=UTF-8


import jalf
import json
import logging
import os.path
import os
import shutil
from subprocess import Popen


LOG = logging.getLogger(__name__)
PLUGIN_DIR = os.path.dirname(__file__)
CHROME_EXE = 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


CHROME_OPTS = {
    'crsLessApps': {
        'type': 'boolean',
        'desc': 'Create apps without using CRX packages',
        'option': '--enable-crxless-web-apps'
    },
    'easyExtensionInstall': {
        'type': 'boolean',
        'desc': 'Enable easy script installation from outside the store',
        'option': '--easy-off-store-extension-install'
    },
    'allowFileAccess': {
        'type': 'boolean',
        'desc': 'Allow file:// access',
        'option': '--allow-file-access-from-files'
    },
    'appCacheDisable': {
        'type': 'boolean',
        'desc': 'Disable the application cache',
        'option': '--disable-application-cache'
    },
    'allowOutdatedPlugins': {
        'type': 'boolean',
        'desc': 'Allow outdated plugins',
        'option': '--allow-outdated-plugins'
    },
    'allowInsecureContent': {
        'type': 'boolean',
        'desc': 'Allow insecure content over http',
        'option': '--allow-running-insecure-content'
    },
    'alwaysAuthorizePlugins': {
        'type': 'boolean',
        'desc': "Don't require authorization for plugins",
        'option': '--always-authorize-plugins'
    }
}


class Prism(object):
    def __init__(self, name, workflow, desc=None):
        self.name = name
        self.workflow = workflow
        self.description = desc
        self.app_dir = os.path.join(workflow.data_dir, '{}.app'.format(name))
        self.conf_file = os.path.join(self.app_dir, 'prism.json')
        self.cache_dir = os.path.join(workflow.cache_dir, name)

        if os.path.exists(self.conf_file):
            self.load_config()

    def __str__(self):
        return self.name

    def load_config(self):
        with open(self.conf_file, 'r') as cf:
            config = json.load(cf)
            self.description = config.get('description', self.description)

    def save_config(self):
        config = {}
        if self.description:
            config['description'] = self.description
        with open(self.conf_file, 'wt') as cf:
            json.dump(config, cf)

    def start(self):
        Popen(['open', self.app_dir])

    def exists(self):
        return os.path.exists(self.app_dir)

    def create(self):
        '''Create this prism.'''
        if os.path.exists(self.app_dir):
            raise Exception('App dir for {} already exists'.format(self.name))
        if os.path.exists(self.app_dir):
            raise Exception('Cache dir for {} already exists'.format(
                            self.name))

        os.mkdir(self.app_dir)
        os.mkdir(self.cache_dir)

        self.save_config()

        plfile = os.path.join(PLUGIN_DIR, 'resources', 'Info.plist.tmpl')
        with open(plfile, 'r') as template:
            plist_tmpl = template.read()

        bundle_id = '{}.{}'.format(self.workflow.bundle_id, self.name)
        plist = plist_tmpl.format(bundle_name='Chrome Prism',
                                  bundle_id=bundle_id)

        contents_dir = os.path.join(self.app_dir, 'Contents')
        os.mkdir(contents_dir)
        with open(os.path.join(contents_dir, 'Info.plist'), 'wt') as plfile:
            plfile.write(plist)

        mac_dir = os.path.join(contents_dir, 'MacOS')
        os.mkdir(mac_dir)
        script = os.path.join(mac_dir, 'run.sh')
        with open(script, 'wt') as sf:
            sf.write('#!/bin/sh\n')
            sf.write('exec "{}" \\\n'.format(CHROME_EXE))
            sf.write('  --no-first-run \\\n')
            sf.write("  --user-data-dir='{}'\n".format(self.cache_dir))
        os.chmod(script, 0744)

        res_dir = os.path.join(contents_dir, 'Resources')
        os.mkdir(res_dir)
        icon_file = os.path.join(PLUGIN_DIR, 'resources', 'icon.icns')
        shutil.copy(icon_file, res_dir)

    def delete(self):
        '''Delete this prism.'''
        shutil.rmtree(self.app_dir)
        shutil.rmtree(self.cache_dir)


class Workflow(jalf.AlfredWorkflow):
    def _load_config(self, prism_name):
        cfg_file = os.path.join(self.data_dir, '{}.json'.format(prism_name))
        with open(cfg_file, 'r') as cf:
            data = json.load(cf)
        return data

    def _get_prisms(self):
        '''Get a list of existing prisms.'''
        prisms = []
        apps = [a for a in os.listdir(self.data_dir) if a.endswith('.app')]
        for app in apps:
            name = app[:-4]
            prisms.append(Prism(name, self))
        return prisms

    def tell_list(self, query=None):
        '''Return the list of available prisms.'''
        items = []

        LOG.debug('listing with query "%s"', query)

        if query.startswith('+'):
            prism_name = query[1:].strip()
            desc = None

            if ' ' in prism_name:
                prism_name, sep, desc = prism_name.partition(' ')

            if prism_name:
                items.append(jalf.Item('Create a new prism "{}"...'.format(
                                       prism_name), arg=query, valid=True))
                if desc:
                    items[-1].subtitle = desc
            else:
                items.append(jalf.Item('Create a new prism...', arg='+',
                                       valid=True))

        elif query.startswith('?'):
            items.append(jalf.Item("Show help", arg='?', valid=True))

        else:
            prisms = self._get_prisms()
            for prism in prisms:
                name = prism.name
                LOG.debug('adding item for "{}"'.format(name))
                items.append(jalf.Item(name, arg=name, valid=True))
                if prism.description:
                    items[-1].subtitle = prism.description
            if query:
                items = jalf.fuzzy_match_list(query, items,
                                              key=lambda x: x.title)

        if len(items) == 0:
            items.append(jalf.Item('No prisms found'))

        return items

    def do_create(self, prism_name=None):
        '''Create a new prism.'''
        LOG.debug('do_create(%s)', prism_name)

        if not prism_name:
            LOG.debug('no prism name given')
            btn, prism_name = jalf.get_from_user(
                'Prism name', 'Give a name for this prism. The name may not '
                'contain spaces. You may add a description after the name '
                '(e.g. myPrism This is a flashy prism)')
            if btn == ('Cancel'):
                return

        desc = None
        if ' ' in prism_name:
            LOG.debug('splitting description from name')
            prism_name, sep, desc = prism_name.partition(' ')

        prism_app = Prism(prism_name, self, desc)
        if prism_app.exists():
            raise Exception('A prism named {} already exists'.format(
                            prism_name))

        LOG.debug('creating prism %s', prism_name)
        prism_app.create()

        self.puts('Created prism {}'.format(prism_name))

    def do_edit(self, prism_name):
        '''Edit a prism config.'''
        LOG.debug('editing prism %s', prism_name)
        prism = Prism(prism_name, self)
        if not prism.exists():
            raise Exception('There is no prism named {}'.format(prism_name))
        LOG.debug('opening prism conf file at %s', prism.conf_file)
        Popen(['open', prism.conf_file])

    def do_delete(self, prism_name):
        '''Delete an existing prism.'''
        answer = jalf.get_confirmation('Delete prism',
                                       'Are you sure you want to delete '
                                       '{}?'.format(prism_name),
                                       default='Yes')
        LOG.debug('got answer: %s', answer)
        if answer != 'Yes':
            return

        LOG.debug('deleting prism %s', prism_name)
        Prism(prism_name, self).delete()
        self.puts('Deleted prism {}'.format(prism_name))

    def do_start(self, prism_name=None):
        '''Start the named prism.'''
        LOG.debug('do_start()')

        if prism_name.startswith('+'):
            LOG.debug('creating a prism')
            prism_name = prism_name[1:].strip()
            self.do_create(prism_name)
        elif prism_name == '?':
            LOG.debug('showing help')
            message = jalf.BUNDLE_INFO['readme']
            jalf.show_message('Chrome Prism Help', message)
        else:
            LOG.debug('starting prism %s', prism_name)
            Prism(prism_name, self).start()


if __name__ == '__main__':
    from sys import argv
    ap = Workflow()
    getattr(ap, argv[1])(*argv[2:])
