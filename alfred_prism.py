#!/usr/bin/env python
# coding=UTF-8


# Create and manage separate instances of Chrome
#
# Prism apps are stored in the workflow's data directory, and app caches are
# stored in the workflow cache directory.
#
# Prisms are stored in random directories defined at creation time.


import jcalfred
import json
import logging
import os.path
import os
import shutil
from subprocess import Popen


LOG = logging.getLogger(__name__)
PLUGIN_DIR = os.path.dirname(__file__)
CHROME_EXE = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def load_commented_json(json_file):
    '''Load a JSON file containing JavaScript-style line comments ('//')'''
    data = [n for n in json_file.readlines() if not
            n.lstrip().startswith('//')]
    return json.loads(''.join(data))


def write_instructions(json_file):
    with open('conf_instructions.txt') as conf_instr:
        instructions = conf_instr.read()
    json_file.write(instructions)


class Prism(object):
    def __init__(self, workflow, name, description=None):
        self.workflow = workflow
        self.description = description
        self._set_name(name)
        self.options = []

        if os.path.exists(self.conf_file):
            self.load_config()

    def __str__(self):
        return self.name

    def _set_name(self, name):
        self.name = name
        self.app_dir = os.path.join(self.workflow.data_dir, '%s.app' % name)
        self.conf_file = os.path.join(self.app_dir, 'prism.json')
        self.cache_dir = os.path.join(self.workflow.cache_dir, name)

    def load_config(self):
        with open(self.conf_file, 'r') as cf:
            config = load_commented_json(cf)
            self.description = config.get('description', self.description)
            self.options = config.get('options', self.options)

    def save_config(self):
        config = {'options': self.options}
        if self.description:
            config['description'] = self.description
        with open(self.conf_file, 'wt') as cf:
            write_instructions(cf)
            json.dump(config, cf, indent=2)

    def start(self, url=None):
        # rebuild the run script to agree with the current config
        self.build_script()
        cmd = ['open', self.app_dir]
        if url:
            cmd += ['--args', url]
        LOG.debug('running command: %s', cmd)
        Popen(cmd)

    def exists(self):
        return os.path.exists(self.app_dir)

    def build_script(self):
        contents_dir = os.path.join(self.app_dir, 'Contents')
        mac_dir = os.path.join(contents_dir, 'MacOS')
        script = os.path.join(mac_dir, 'run.sh')

        with open(script, 'wt') as sf:
            sf.write('#!/bin/sh\n')
            sf.write('exec "%s" \\\n' % CHROME_EXE)
            sf.write('  --no-first-run \\\n')
            sf.write("  --user-data-dir='%s'" % self.cache_dir)
            for opt in self.options:
                sf.write(" \\\n  %s" % opt)
            sf.write('\n')
        os.chmod(script, 0744)

    def create(self):
        '''Create this prism.'''
        if os.path.exists(self.app_dir):
            raise Exception('App dir for %s already exists' % self.name)
        if os.path.exists(self.app_dir):
            raise Exception('Cache dir for %s already exists' % self.name)

        os.mkdir(self.app_dir)
        os.mkdir(self.cache_dir)

        self.save_config()

        plfile = os.path.join(PLUGIN_DIR, 'resources', 'Info.plist.tmpl')
        with open(plfile, 'r') as template:
            plist_tmpl = template.read()

        bundle_id = '%s.%s' % (self.workflow.bundle_id, self.name)
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

    def rename(self, new_name):
        '''Rename this prism'''
        old_app_dir = self.app_dir
        old_cache_dir = self.cache_dir
        self._set_name(new_name)
        os.rename(old_app_dir, self.app_dir)
        os.rename(old_cache_dir, self.cache_dir)

    def delete(self):
        '''Delete this prism.'''
        shutil.rmtree(self.app_dir)
        shutil.rmtree(self.cache_dir)


class Workflow(jcalfred.Workflow):
    def _load_config(self, prism_name):
        cfg_file = os.path.join(self.data_dir, '%s.json' % prism_name)
        with open(cfg_file, 'r') as cf:
            data = json.load(cf)
        return data

    def _get_prisms(self):
        '''Get a list of existing prisms.'''
        prisms = []
        apps = [a for a in os.listdir(self.data_dir) if a.endswith('.app')]
        for app in apps:
            name = app[:-4]
            prisms.append(Prism(self, name))
        return prisms

    def _load_help(self):
        '''Load help items from the readme.'''
        items = []
        message = self.info.readme
        for line in [n for n in message.split('\n') if n.startswith('* ')]:
            items.append(jcalfred.Item(line[2:]))
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
                items.append(jcalfred.Item(
                    'Create a new prism "%s"...' % prism_name,
                    arg=query, valid=True))
                if desc:
                    items[-1].subtitle = desc
            else:
                items.append(jcalfred.Item('Create a new prism...', arg='+',
                                           valid=True))

        elif query.startswith('?'):
            items += self._load_help()

        else:
            for prism in self._get_prisms():
                LOG.debug('adding item for "%s"', prism)
                name = prism.name
                items.append(jcalfred.Item(name, arg=prism.name, valid=True))
                if prism.description:
                    items[-1].subtitle = prism.description

            if query:
                query = query.lstrip()
                parts = query.split()
                LOG.debug('query parts: %s', parts)
                name = parts[0].strip()
                if ' ' in query:
                    items = [i for i in items if i.title == name]
                    if len(items) > 0:
                        item = items[0]
                        if len(parts) > 1:
                            item.arg += '|' + parts[1].strip()
                        LOG.debug('item arg: %s', item.arg)
                        items = [item]
                else:
                    items = self.fuzzy_match_list(name, items,
                                                  key=lambda x: x.title)

        if len(items) == 0:
            items.append(jcalfred.Item('No prisms found'))
            items.append(jcalfred.Item("Type '+' to create a new prism"))
            items.append(jcalfred.Item("Type '?' for more help"))

        return items

    def do_create(self, prism_name=None):
        '''Create a new prism.'''
        LOG.debug('do_create(%s)', prism_name)

        if not prism_name:
            LOG.debug('no prism name given')
            btn, prism_name = self.get_from_user(
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
            raise Exception('A prism named %s already exists' % prism_name)

        LOG.debug('creating prism %s', prism_name)
        prism_app.create()

        self.puts('Created prism %s' % prism_name)

    def do_edit(self, name):
        '''Edit a prism config.'''
        prism = Prism(self, name)
        LOG.debug('editing prism %s', prism)
        if not prism.exists():
            raise Exception('There is no prism named %s' % name)
        LOG.debug('opening prism conf file at %s', prism.conf_file)
        Popen(['open', prism.conf_file])

    def do_open(self, name):
        '''Open a prism in Finder.'''
        prism = Prism(self, name)
        LOG.debug('opening prism %s', prism)
        if not prism.exists():
            raise Exception('There is no prism named %s' % name)
        Popen(['open', '-R', prism.conf_file])

    def do_rename(self, name):
        '''Delete an existing prism.'''
        prism = Prism(self, name)
        while True:
            btn, answer = self.get_from_user('Rename %s' % prism, 'New name')
            if btn == 'Cancel':
                return
            new_name = answer.strip()
            if ' ' in new_name:
                self.show_message('Prism names may not contain spaces')
                continue
            LOG.debug('renaming prism %s to %s', prism, new_name)
            old_name = prism.name
            prism.rename(new_name)
            self.puts('Renamed prism %s to %s' % (old_name, new_name))
            break

    def do_delete(self, name):
        '''Delete an existing prism.'''
        prism = Prism(self, name)
        answer = self.get_confirmation('Delete prism',
                                       'Are you sure you want to delete '
                                       '%s?' % prism, default='Yes')
        LOG.debug('got answer: %s', answer)
        if answer != 'Yes':
            return

        LOG.debug('deleting prism %s', prism)
        prism.delete()
        self.puts('Deleted prism %s' % prism)

    def do_start(self, arg=None):
        '''Start the named prism.'''
        LOG.debug('do_start(%s)', arg)

        if '|' in arg:
            name, url = arg.split('|')
        else:
            name = arg
            url = None

        if name.startswith('+'):
            LOG.debug('creating a prism')
            prism_name = name[1:].strip()
            self.do_create(prism_name)
        elif name == '?':
            LOG.debug('showing help')
            message = self.info.readme
            self.show_message('Chrome Prism Help', message)
        else:
            LOG.debug('starting prism %s', name)
            Prism(self, name).start(url)


if __name__ == '__main__':
    from sys import argv
    ap = Workflow()
    getattr(ap, argv[1])(*argv[2:])
