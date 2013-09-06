# Copyright 2013, Big Switch Networks, Inc.
#
# LoxiGen is licensed under the Eclipse Public License, version 1.0 (EPL), with
# the following special exception:
#
# LOXI Exception
#
# As a special exception to the terms of the EPL, you may distribute libraries
# generated by LoxiGen (LoxiGen Libraries) under the terms of your choice, provided
# that copyright and licensing notices generated by LoxiGen are not altered or removed
# from the LoxiGen Libraries and the notice provided below is (i) included in
# the LoxiGen Libraries, if distributed in source code form and (ii) included in any
# documentation for the LoxiGen Libraries, if distributed in binary form.
#
# Notice: "Copyright 2013, Big Switch Networks, Inc. This library was generated by the LoxiGen Compiler."
#
# You may not use this file except in compliance with the EPL or LOXI Exception. You may obtain
# a copy of the EPL at:
#
# http://www.eclipse.org/legal/epl-v10.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# EPL for the specific language governing permissions and limitations
# under the EPL.

"""
@brief Main Java Generation module
"""

import pdb
import os
import shutil

import of_g
from loxi_ir import *
import lang_java
import test_data
from import_cleaner import ImportCleaner

import loxi_utils.loxi_utils as loxi_utils

import java_gen.java_model as java_model

def gen_all_java(out, name):
    basedir= '%s/openflowj' % of_g.options.install_dir
    print "Outputting to %s" % basedir
    if os.path.exists(basedir):
        shutil.rmtree(basedir)
    os.makedirs(basedir)
    copy_prewrite_tree(basedir)

    gen = JavaGenerator(basedir)
    gen.create_of_interfaces()
    gen.create_of_classes()
    gen.create_of_const_enums()
    gen.create_of_factories()

    with open('%s/README.java-lang' % os.path.dirname(__file__)) as readme_src:
        out.writelines(readme_src.readlines())
    out.close()


class JavaGenerator(object):
    templates_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')

    def __init__(self, basedir):
        self.basedir = basedir
        self.java_model = java_model.model

    def render_class(self, clazz, template, src_dir=None, **context):
        if not src_dir:
            src_dir = "src/main/java/"

        context['class_name'] = clazz.name
        context['package'] = clazz.package
        context['template_dir'] = self.templates_dir

        filename = os.path.join(self.basedir, src_dir, "%s/%s.java" % (clazz.package.replace(".", "/"), clazz.name))
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        prefix = '//::(?=[ \t]|$)'
        print "filename: %s" % filename
        with open(filename, "w") as f:
            loxi_utils.render_template(f, template, [self.templates_dir], context, prefix=prefix)
        
        try:
            cleaner = ImportCleaner(filename)
            cleaner.find_used_imports()
            cleaner.rewrite_file(filename)
        except:
            print 'Cannot clean imports from file %s' % filename
        

    def create_of_const_enums(self):
        for enum in self.java_model.enums:
            if enum.name in ["OFPort"]:
                continue
            self.render_class(clazz=enum,
                    template='const.java', enum=enum, all_versions=self.java_model.versions)

            for version in enum.versions:
                clazz = java_model.OFGenericClass(package="org.projectfloodlight.openflow.protocol.ver{}".format(version.of_version), name="{}SerializerVer{}".format(enum.name, version.of_version))
                self.render_class(clazz=clazz, template="const_serializer.java", enum=enum, version=version)

    def create_of_interfaces(self):
        """ Create the base interfaces for of classes"""
        for interface in self.java_model.interfaces:
            #if not utils.class_is_message(interface.c_name):
            #    continue
            self.render_class(clazz=interface,
                    template="of_interface.java", msg=interface)

    def create_of_classes(self):
        """ Create the OF classes with implementations for each of the interfaces and versions """
        for interface in self.java_model.interfaces:
            for java_class in interface.versioned_classes:
                if self.java_model.generate_class(java_class):
                    if not java_class.is_virtual:
                        self.render_class(clazz=java_class,
                                template='of_class.java', version=java_class.version, msg=java_class,
                                impl_class=java_class.name)

                        self.create_unit_test(java_class.unit_test)
                    else:
                        disc = java_class.discriminator
                        if disc:
                            self.render_class(clazz=java_class,
                                template='of_virtual_class.java', version=java_class.version, msg=java_class,
                                impl_class=java_class.name, model=self.java_model)
                        else:
                            print "Class %s virtual but no discriminator" % java_class.name
                else:
                    print "Class %s ignored by generate_class" % java_class.name

    def create_unit_test(self, unit_tests):
        if unit_tests.has_test_data:
            for i in range(unit_tests.length):
                unit_test = unit_tests.get_test_unit(i)
                if unit_test.has_test_data:
                    self.render_class(clazz=unit_test,
                            template='unit_test.java', src_dir="src/test/java",
                            version=unit_test.java_class.version,
                            test=unit_test, msg=unit_test.java_class,
                            test_data=unit_test.test_data)

    def create_of_factories(self):
        for factory in self.java_model.of_factories:
            self.render_class(clazz=factory, template="of_factory_interface.java", factory=factory)
            for factory_class in factory.factory_classes:
                self.render_class(clazz=factory_class, template="of_factory_class.java", factory=factory_class, model=self.java_model)
            self.render_class(clazz=java_model.OFGenericClass(package="org.projectfloodlight.openflow.protocol", name="OFFactories"), template="of_factories.java", versions=self.java_model.versions)

def copy_prewrite_tree(basedir):
    """ Recursively copy the directory structure from ./java_gen/pre-write
       into $basedir"""
    print "Copying pre-written files into %s" % basedir
    #subprocess.call("cd java_gen/pre-written && tar cpf - pom.xml | ( cd ../../%s && tar xvpf - )" % basedir,
    #        shell=True)
    os.symlink(os.path.abspath("%s/pre-written/pom.xml" %  os.path.dirname(__file__)), "%s/pom.xml" % basedir)
