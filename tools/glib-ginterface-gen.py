#!/usr/bin/python

# glib-ginterface-gen.py: service-side interface generator
#
# Generate dbus-glib 0.x service GInterfaces from the Telepathy specification.
# The master copy of this program is in the telepathy-glib repository -
# please make any changes there.
#
# Copyright (C) 2006, 2007 Collabora Limited
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os.path
import xml.dom.minidom

from libglibcodegen import Signature, type_to_gtype, cmp_by_name, \
        camelcase_to_lower, NS_TP, dbus_gutils_wincaps_to_uscore, \
        signal_to_marshal_name


NS_TP = "http://telepathy.freedesktop.org/wiki/DbusSpec#extensions-v0"

class Generator(object):

    def __init__(self, dom, prefix, basename, signal_marshal_prefix,
                 headers, end_headers, not_implemented_func,
                 allow_havoc):
        self.dom = dom
        self.__header = []
        self.__body = []

        assert prefix.endswith('_')
        assert not signal_marshal_prefix.endswith('_')

        self.Prefix_ = prefix
        self.Prefix = prefix.replace('_', '')
        self.prefix_ = prefix.lower()
        self.PREFIX_ = prefix.upper()

        self.signal_marshal_prefix = signal_marshal_prefix
        self.headers = headers
        self.end_headers = end_headers
        self.not_implemented_func = not_implemented_func
        self.allow_havoc = allow_havoc

    def h(self, s):
        self.__header.append(s)

    def b(self, s):
        self.__body.append(s)

    def do_node(self, node):
        node_name = node.getAttribute('name').replace('/', '')
        node_name_mixed = self.node_name_mixed = node_name.replace('_', '')
        node_name_lc = self.node_name_lc = node_name.lower()
        node_name_uc = self.node_name_uc = node_name.upper()

        interfaces = node.getElementsByTagName('interface')
        assert len(interfaces) == 1, interfaces
        interface = interfaces[0]
        self.iface_name = interface.getAttribute('name')

        tmp = node.getAttribute('causes-havoc')
        if tmp and not self.allow_havoc:
            raise AssertionError('%s is %s' % (self.iface_name, tmp))

        self.b('const DBusGObjectInfo dbus_glib_%s%s_object_info;'
               % (self.prefix_, node_name_lc))
        self.b('')

        methods = interface.getElementsByTagName('method')
        signals = interface.getElementsByTagName('signal')

        self.b('struct _%s%sClass {' % (self.Prefix, node_name_mixed))
        self.b('    GTypeInterface parent_class;')
        for method in methods:
            self.b('    %s %s;' % self.get_method_impl_names(method))
        self.b('};')
        self.b('')

        if signals:
            self.b('enum {')
            for signal in signals:
                self.b('    %s,' % self.get_signal_const_entry(signal))
            self.b('    N_%s_SIGNALS' % node_name_uc)
            self.b('};')
            self.b('static guint %s_signals[N_%s_SIGNALS] = {0};'
                   % (node_name_lc, node_name_uc))
            self.b('')

        self.b('static void %s%s_base_init (gpointer klass);'
               % (self.prefix_, node_name_lc))
        self.b('')

        self.b('GType')
        self.b('%s%s_get_type (void)'
               % (self.prefix_, node_name_lc))
        self.b('{')
        self.b('  static GType type = 0;')
        self.b('')
        self.b('  if (G_UNLIKELY (type == 0))')
        self.b('    {')
        self.b('      static const GTypeInfo info = {')
        self.b('        sizeof (%s%sClass),' % (self.Prefix, node_name_mixed))
        self.b('        %s%s_base_init, /* base_init */'
               % (self.prefix_, node_name_lc))
        self.b('        NULL, /* base_finalize */')
        self.b('        NULL, /* class_init */')
        self.b('        NULL, /* class_finalize */')
        self.b('        NULL, /* class_data */')
        self.b('        0,')
        self.b('        0, /* n_preallocs */')
        self.b('        NULL /* instance_init */')
        self.b('      };')
        self.b('')
        self.b('      type = g_type_register_static (G_TYPE_INTERFACE,')
        self.b('          "%s%s", &info, 0);' % (self.Prefix, node_name_mixed))
        self.b('    }')
        self.b('')
        self.b('  return type;')
        self.b('}')
        self.b('')

        self.h('/**')
        self.h(' * %s%s:' % (self.Prefix, node_name_mixed))
        self.h(' *')
        self.h(' * Dummy typedef representing any implementation of this '
               'interface.')
        self.h(' */')
        self.h('typedef struct _%s%s %s%s;'
               % (self.Prefix, node_name_mixed, self.Prefix, node_name_mixed))
        self.h('')
        self.h('/**')
        self.h(' * %s%sClass:' % (self.Prefix, node_name_mixed))
        self.h(' *')
        self.h(' * The class of %s%s.' % (self.Prefix, node_name_mixed))
        self.h(' */')
        self.h('typedef struct _%s%sClass %s%sClass;'
               % (self.Prefix, node_name_mixed, self.Prefix, node_name_mixed))
        self.h('')
        self.h('GType %s%s_get_type (void);'
               % (self.prefix_, node_name_lc))

        main_prefix, sub_prefix = self.PREFIX_.split('_', 1)
        main_prefix += '_'
        sub_prefix = '_' + sub_prefix
        # FOO_ -> (FOO_, _)
        # FOO_SVC_ -> (FOO_, _SVC_)

        gtype = self.current_gtype = \
                main_prefix + 'TYPE' + sub_prefix + node_name_uc
        classname = self.Prefix + node_name_mixed

        self.h('#define %s \\\n  (%s%s_get_type ())'
               % (gtype, self.prefix_, node_name_lc))
        self.h('#define %s%s(obj) \\\n'
               '  (G_TYPE_CHECK_INSTANCE_CAST((obj), %s, %s))'
               % (self.PREFIX_, node_name_uc, gtype, classname))
        self.h('#define %sIS%s%s(obj) \\\n'
               '  (G_TYPE_CHECK_INSTANCE_TYPE((obj), %s))'
               % (main_prefix, sub_prefix, node_name_uc, gtype))
        self.h('#define %s%s_GET_CLASS(obj) \\\n'
               '  (G_TYPE_INSTANCE_GET_INTERFACE((obj), %s, %sClass))'
               % (self.PREFIX_, node_name_uc, gtype, classname))
        self.h('')
        self.h('')

        base_init_code = []

        for method in methods:
            self.do_method(method)

        for signal in signals:
            base_init_code.extend(self.do_signal(signal))

        self.b('static void')
        self.b('%s%s_base_init (gpointer klass)'
               % (self.prefix_, node_name_lc))
        self.b('{')
        self.b('  static gboolean initialized = FALSE;')
        self.b('')
        self.b('  if (initialized)')
        self.b('    return;')
        self.b('')
        self.b('  initialized = TRUE;')
        self.b('')
        for s in base_init_code:
            self.b(s)
        self.b('  dbus_g_object_type_install_info (%s%s_get_type (),'
               % (self.prefix_, node_name_lc))
        self.b('      &dbus_glib_%s%s_object_info);'
               % (self.prefix_, node_name_lc))
        self.b('}')

        self.h('')

        self.node_name_mixed = None
        self.node_name_lc = None
        self.node_name_uc = None

    def get_method_impl_names(self, method):
        dbus_method_name = method.getAttribute('name')
        class_member_name = camelcase_to_lower(dbus_method_name)
        stub_name = (self.prefix_ + self.node_name_lc + '_' +
                     class_member_name)
        return (stub_name + '_impl', class_member_name)

    def do_method(self, method):
        assert self.node_name_mixed is not None

        in_class = []

        # Examples refer to Thing.DoStuff (su) -> ii

        # DoStuff
        dbus_method_name = method.getAttribute('name')
        # do_stuff
        class_member_name = camelcase_to_lower(dbus_method_name)
        # void tp_svc_thing_do_stuff (TpSvcThing *, const char *, guint,
        #   DBusGMethodInvocation *);
        stub_name = (self.prefix_ + self.node_name_lc + '_' +
                     class_member_name)
        # typedef void (*tp_svc_thing_do_stuff_impl) (TpSvcThing *,
        #   const char *, guint, DBusGMethodInvocation);
        impl_name = stub_name + '_impl'
        # void tp_svc_thing_return_from_do_stuff (DBusGMethodInvocation *,
        #   gint, gint);
        ret_name = (self.prefix_ + self.node_name_lc + '_return_from_' +
                    class_member_name)

        # Gather arguments
        in_args = []
        out_args = []
        for i in method.getElementsByTagName('arg'):
            name = i.getAttribute('name')
            direction = i.getAttribute('direction') or 'in'
            dtype = i.getAttribute('type')

            assert direction in ('in', 'out')

            if name:
                name = direction + '_' + name
            elif direction == 'in':
                name = direction + str(len(in_args))
            else:
                name = direction + str(len(out_args))

            ctype, gtype, marshaller, pointer = type_to_gtype(dtype)

            if pointer:
                ctype = 'const ' + ctype

            struct = (ctype, name)

            if direction == 'in':
                in_args.append(struct)
            else:
                out_args.append(struct)

        # Implementation type declaration (in header, docs in body)
        self.b('/**')
        self.b(' * %s:' % impl_name)
        self.b(' * @self: The object implementing this interface')
        for (ctype, name) in in_args:
            self.b(' * @%s: %s (FIXME, generate documentation)'
                   % (name, ctype))
        self.b(' * @context: Used to return values or throw an error')
        self.b(' *')
        self.b(' * The signature of an implementation of the D-Bus method')
        self.b(' * %s on interface %s.' % (dbus_method_name, self.iface_name))
        self.b(' */')
        self.h('typedef void (*%s) (%s%s *self,'
          % (impl_name, self.Prefix, self.node_name_mixed))
        for (ctype, name) in in_args:
            self.h('    %s%s,' % (ctype, name))
        self.h('    DBusGMethodInvocation *context);')

        # Class member (in class definition)
        in_class.append('    %s %s;' % (impl_name, class_member_name))

        # Stub definition (in body only - it's static)
        self.b('static void')
        self.b('%s (%s%s *self,'
           % (stub_name, self.Prefix, self.node_name_mixed))
        for (ctype, name) in in_args:
            self.b('    %s%s,' % (ctype, name))
        self.b('    DBusGMethodInvocation *context)')
        self.b('{')
        self.b('  %s impl = (%s%s_GET_CLASS (self)->%s);'
          % (impl_name, self.PREFIX_, self.node_name_uc, class_member_name))
        self.b('')
        self.b('  if (impl != NULL)')
        tmp = ['self'] + [name for (ctype, name) in in_args] + ['context']
        self.b('    {')
        self.b('      (impl) (%s);' % ',\n        '.join(tmp))
        self.b('    }')
        self.b('  else')
        self.b('    {')
        if self.not_implemented_func:
            self.b('      %s (context);' % self.not_implemented_func)
        else:
            self.b('      GError e = { DBUS_GERROR, ')
            self.b('           DBUS_GERROR_UNKNOWN_METHOD,')
            self.b('           "Method not implemented" };')
            self.b('')
            self.b('      dbus_g_method_return_error (context, &e);')
        self.b('    }')
        self.b('}')
        self.b('')

        # Fixup for dbus-binding-tool crack
        dbus_glib_name = (self.prefix_ + self.node_name_lc + '_' +
                          dbus_gutils_wincaps_to_uscore(dbus_method_name))
        if dbus_glib_name != stub_name:
            self.b('#define %s %s' % (dbus_glib_name, stub_name))

        # Implementation registration (in both header and body)
        self.h('void %s%s_implement_%s (%s%sClass *klass, %s impl);'
               % (self.prefix_, self.node_name_lc, class_member_name,
                  self.Prefix, self.node_name_mixed, impl_name))

        self.b('/**')
        self.b(' * %s%s_implement_%s:'
               % (self.prefix_, self.node_name_lc, class_member_name))
        self.b(' * @klass: A class whose instances implement this interface')
        self.b(' * @impl: A callback used to implement the %s D-Bus method'
               % dbus_method_name)
        self.b(' *')
        self.b(' * Register an implementation for the %s method in the vtable'
               % dbus_method_name)
        self.b(' * of an implementation of this interface. To be called from')
        self.b(' * the interface init function.')
        self.b(' */')
        self.b('void')
        self.b('%s%s_implement_%s (%s%sClass *klass, %s impl)'
               % (self.prefix_, self.node_name_lc, class_member_name,
                  self.Prefix, self.node_name_mixed, impl_name))
        self.b('{')
        self.b('  klass->%s = impl;' % class_member_name)
        self.b('}')
        self.b('')

        # Return convenience function (static inline, in header)
        self.h('/**')
        self.h(' * %s:' % ret_name)
        self.h(' * @context: The D-Bus method invocation context')
        for (ctype, name) in out_args:
            self.h(' * @%s: %s (FIXME, generate documentation)'
                   % (name, ctype))
        self.h(' *')
        self.h(' * Return successfully by calling dbus_g_method_return().')
        self.h(' * This inline function exists only to provide type-safety.')
        self.h(' */')
        tmp = (['DBusGMethodInvocation *context'] +
               [ctype + name for (ctype, name) in out_args])
        self.h('static inline')
        self.h('/* this comment is to stop gtkdoc realising this is static */')
        self.h(('void %s (' % ret_name) + (',\n    '.join(tmp)) + ');')
        self.h('static inline void')
        self.h(('%s (' % ret_name) + (',\n    '.join(tmp)) + ')')
        self.h('{')
        tmp = ['context'] + [name for (ctype, name) in out_args]
        self.h('  dbus_g_method_return (' + ',\n      '.join(tmp) + ');')
        self.h('}')
        self.h('')

        return in_class

    def get_signal_const_entry(self, signal):
        assert self.node_name_uc is not None
        return ('SIGNAL_%s_%s'
                % (self.node_name_uc, signal.getAttribute('name')))

    def do_signal(self, signal):
        assert self.node_name_mixed is not None

        in_base_init = []

        # for signal: Thing::StuffHappened (s, u)
        # we want to emit:
        # void tp_svc_thing_emit_stuff_happened (gpointer instance,
        #    const char *arg0, guint arg1);

        dbus_name = signal.getAttribute('name')
        stub_name = (self.prefix_ + self.node_name_lc + '_emit_' +
                     camelcase_to_lower(dbus_name))
        const_name = self.get_signal_const_entry(signal)

        # Gather arguments
        args = []
        for i in signal.getElementsByTagName('arg'):
            name = i.getAttribute('name')
            dtype = i.getAttribute('type')
            tp_type = i.getAttribute('tp:type')

            if name:
                name = 'arg_' + name
            else:
                name = 'arg' + str(len(args))

            ctype, gtype, marshaller, pointer = type_to_gtype(dtype)

            if pointer:
                ctype = 'const ' + ctype

            struct = (ctype, name, gtype)
            args.append(struct)

        tmp = (['gpointer instance'] +
               [ctype + name for (ctype, name, gtype) in args])

        self.h(('void %s (' % stub_name) + (',\n    '.join(tmp)) + ');')

        # FIXME: emit docs

        self.b('/**')
        self.b(' * %s:' % stub_name)
        self.b(' * @instance: The object implementing this interface')
        for (ctype, name, gtype) in args:
            self.b(' * @%s: %s (FIXME, generate documentation)'
                   % (name, ctype))
        self.b(' *')
        self.b(' * Type-safe wrapper around g_signal_emit to emit the')
        self.b(' * %s signal on interface %s.'
               % (dbus_name, self.iface_name))
        self.b(' */')

        self.b('void')
        self.b(('%s (' % stub_name) + (',\n    '.join(tmp)) + ')')
        self.b('{')
        self.b('  g_assert (instance != NULL);')
        self.b('  g_assert (G_TYPE_CHECK_INSTANCE_TYPE (instance, %s));'
               % (self.current_gtype))
        tmp = (['instance', '%s_signals[%s]' % (self.node_name_lc, const_name),
                '0'] + [name for (ctype, name, gtype) in args])
        self.b('  g_signal_emit (' + ',\n      '.join(tmp) + ');')
        self.b('}')
        self.b('')

        in_base_init.append('  %s_signals[%s] ='
                            % (self.node_name_lc, const_name))
        in_base_init.append('  g_signal_new ("%s",'
                % (dbus_gutils_wincaps_to_uscore(dbus_name).replace('_', '-')))
        in_base_init.append('      G_OBJECT_CLASS_TYPE (klass),')
        in_base_init.append('      G_SIGNAL_RUN_LAST|G_SIGNAL_DETAILED,')
        in_base_init.append('      0,')
        in_base_init.append('      NULL, NULL,')
        in_base_init.append('      %s,'
                % signal_to_marshal_name(signal, self.signal_marshal_prefix))
        in_base_init.append('      G_TYPE_NONE,')
        tmp = ['%d' % len(args)] + [gtype for (ctype, name, gtype) in args]
        in_base_init.append('      %s);' % ',\n      '.join(tmp))
        in_base_init.append('')

        return in_base_init

    def __call__(self):
        self.h('#include <glib-object.h>')
        self.h('#include <dbus/dbus-glib.h>')
        self.h('')
        self.h('G_BEGIN_DECLS')
        self.h('')

        self.b('#include "%s.h"' % basename)
        self.b('')
        for header in self.headers:
            self.b('#include %s' % header)
        self.b('')

        nodes = self.dom.getElementsByTagName('node')
        nodes.sort(cmp_by_name)

        for node in nodes:
            self.do_node(node)

        self.h('')
        self.h('G_END_DECLS')

        self.b('')
        for header in self.end_headers:
            self.b('#include %s' % header)

        self.h('')
        self.b('')
        open(basename + '.h', 'w').write('\n'.join(self.__header))
        open(basename + '.c', 'w').write('\n'.join(self.__body))


def cmdline_error():
    print """\
usage:
    gen-ginterface [OPTIONS] xmlfile Prefix_
options:
    --include='<header.h>' (may be repeated)
    --include='"header.h"' (ditto)
    --include-end='"header.h"' (ditto)
        Include extra headers in the generated .c file
    --signal-marshal-prefix='prefix'
        Use the given prefix on generated signal marshallers (default is
        prefix.lower()).
    --filename='BASENAME'
        Set the basename for the output files (default is prefix.lower()
        + 'ginterfaces')
    --not-implemented-func='symbol'
        Set action when methods not implemented in the interface vtable are
        called. symbol must have signature
            void symbol (DBusGMethodInvocation *context)
        and return some sort of "not implemented" error via
            dbus_g_method_return_error (context, ...)
"""
    sys.exit(1)


if __name__ == '__main__':
    from getopt import gnu_getopt

    options, argv = gnu_getopt(sys.argv[1:], '',
                               ['filename=', 'signal-marshal-prefix=',
                                'include=', 'include-end=',
                                'allow-unstable',
                                'not-implemented-func='])

    try:
        prefix = argv[1]
    except IndexError:
        cmdline_error()

    basename = prefix.lower() + 'ginterfaces'
    signal_marshal_prefix = prefix.lower().rstrip('_')
    headers = []
    end_headers = []
    not_implemented_func = ''
    allow_havoc = False

    for option, value in options:
        if option == '--filename':
            basename = value
        elif option == '--signal-marshal-prefix':
            signal_marshal_prefix = value
        elif option == '--include':
            if value[0] not in '<"':
                value = '"%s"' % value
            headers.append(value)
        elif option == '--include-end':
            if value[0] not in '<"':
                value = '"%s"' % value
            end_headers.append(value)
        elif option == '--not-implemented-func':
            not_implemented_func = value
        elif option == '--allow-unstable':
            allow_havoc = True

    try:
        dom = xml.dom.minidom.parse(argv[0])
    except IndexError:
        cmdline_error()

    Generator(dom, prefix, basename, signal_marshal_prefix, headers,
              end_headers, not_implemented_func, allow_havoc)()