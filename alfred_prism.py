#!/usr/bin/env python
# coding=UTF-8


# Create and manage separate instances of Chrome
#
# Prism apps are stored in the workflow's data directory, and app caches are
# stored in the workflow cache directory.
#
# Prisms are stored in random directories defined at creation time.


import jalf
import json
import logging
import os.path
import os
import shutil
import uuid
from subprocess import Popen


LOG = logging.getLogger(__name__)
PLUGIN_DIR = os.path.dirname(__file__)
CHROME_EXE = 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


class Prism(object):
    def __init__(self, workflow, name=None, pid=None, description=None):
        if not pid and not name:
            raise Exception('Workflow must have a pid or name')
        if not pid:
            pid = str(uuid.uuid4())

        self.workflow = workflow
        self.name = name
        self.pid = pid
        self.description = description
        self.app_dir = os.path.join(workflow.data_dir, '{}.app'.format(pid))
        self.conf_file = os.path.join(self.app_dir, 'prism.json')
        self.cache_dir = os.path.join(workflow.cache_dir, pid)
        self.options = []

        if os.path.exists(self.conf_file):
            self.load_config()

        if not self.name:
            raise Exception('No name specified or in config file')

    def __str__(self):
        return self.name

    def load_config(self):
        with open(self.conf_file, 'r') as cf:
            config = json.load(cf)
            self.description = config.get('description', self.description)
            self.name = config.get('name', self.name)
            self.options = config.get('options', self.options)

    def save_config(self):
        config = {}
        if self.description:
            config['description'] = self.description
            config['name'] = self.name
            config['options'] = self.options
        with open(self.conf_file, 'wt') as cf:
            json.dump(config, cf, indent=2)

    def start(self):
        # rebuild the run script to agree with the current config
        self.build_script()
        Popen(['open', self.app_dir])

    def exists(self):
        return os.path.exists(self.app_dir)

    def build_script(self):
        contents_dir = os.path.join(self.app_dir, 'Contents')
        mac_dir = os.path.join(contents_dir, 'MacOS')
        script = os.path.join(mac_dir, 'run.sh')

        with open(script, 'wt') as sf:
            sf.write('#!/bin/sh\n')
            sf.write('exec "{}" \\\n'.format(CHROME_EXE))
            sf.write('  --no-first-run \\\n')

            for opt in self.options:
                sf.write("  {} \\\n".format(opt))

            sf.write("  --user-data-dir='{}'\n".format(self.cache_dir))
        os.chmod(script, 0744)

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
        self.build_script()

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
            prisms.append(Prism(self, pid=name))
        return prisms

    def _load_help(self):
        '''Load help items from the readme.'''
        items = []
        message = jalf.BUNDLE_INFO['readme']
        for line in [n for n in message.split('\n') if n.startswith('* ')]:
            items.append(jalf.Item(line[2:]))
        return items

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
            items += self._load_help()

        else:
            prisms = self._get_prisms()
            for prism in prisms:
                LOG.debug('adding item for "{}"'.format(prism.pid))
                name = prism.name
                items.append(jalf.Item(name, arg=prism.pid, valid=True))
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

        prism_app = Prism(self, name=prism_name, description=desc)
        if prism_app.exists():
            raise Exception('A prism named {} already exists'.format(
                            prism_name))

        LOG.debug('creating prism %s', prism_name)
        prism_app.create()

        self.puts('Created prism {}'.format(prism_name))

    def do_edit(self, pid):
        '''Edit a prism config.'''
        LOG.debug('editing prism %s', pid)
        prism = Prism(self, pid=pid)
        if not prism.exists():
            raise Exception('There is no prism with id {}'.format(pid))
        LOG.debug('opening prism conf file at %s', prism.conf_file)
        Popen(['open', prism.conf_file])

    def do_open(self, pid):
        '''Open a prism in Finder.'''
        LOG.debug('opening prism %s', pid)
        prism = Prism(self, pid=pid)
        if not prism.exists():
            raise Exception('There is no prism with id {}'.format(pid))
        Popen(['open', '-R', prism.conf_file])

    def do_delete(self, pid):
        '''Delete an existing prism.'''
        prism = Prism(self, pid=pid)
        answer = jalf.get_confirmation('Delete prism',
                                       'Are you sure you want to delete '
                                       '{}?'.format(prism),
                                       default='Yes')
        LOG.debug('got answer: %s', answer)
        if answer != 'Yes':
            return

        LOG.debug('deleting prism %s', pid)
        prism.delete()
        self.puts('Deleted prism {}'.format(prism.name))

    def do_start(self, pid=None):
        '''Start the named prism.'''
        LOG.debug('do_start()')

        if pid.startswith('+'):
            LOG.debug('creating a prism')
            prism_name = pid[1:].strip()
            self.do_create(prism_name)
        elif pid == '?':
            LOG.debug('showing help')
            message = jalf.BUNDLE_INFO['readme']
            jalf.show_message('Chrome Prism Help', message)
        else:
            LOG.debug('starting prism %s', pid)
            Prism(self, pid=pid).start()


if __name__ == '__main__':
    from sys import argv
    ap = Workflow()
    getattr(ap, argv[1])(*argv[2:])
