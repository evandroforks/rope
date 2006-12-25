import unittest

import rope.base.codeanalyze
import ropetest.refactor.renametest
import ropetest.refactor.extracttest
import ropetest.refactor.movetest
import ropetest.refactor.inlinetest
import ropetest.refactor.change_signature_test
import rope.refactor.introduce_parameter
import ropetest.refactor.importutilstest
from rope.refactor import Undo
from rope.base.exceptions import RefactoringException
from rope.base.project import Project
from rope.refactor.change import *

from ropetest import testutils


class IntroduceFactoryTest(unittest.TestCase):

    def setUp(self):
        super(IntroduceFactoryTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(IntroduceFactoryTest, self).tearDown()
    
    def test_adding_the_method(self):
        code = 'class AClass(object):\n    an_attr = 10\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_the_main_module(self):
        code = 'class AClass(object):\n    an_attr = 10\na_var = AClass()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'\
                   'a_var = AClass.create()'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_with_arguments(self):
        code = 'class AClass(object):\n    def __init__(self, arg):\n        pass\n' \
               'a_var = AClass(10)\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    def __init__(self, arg):\n        pass\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n' \
                   'a_var = AClass.create(10)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_other_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1, 'create')
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.AClass.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_for_non_classes(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write('def a_func():\n    pass\n')
        self.refactoring.introduce_factory(mod, mod.read().index('a_func') + 1, 'create')

    def test_undoing_introduce_factory(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        code1 = 'class AClass(object):\n    an_attr = 10\n'
        mod1.write(code1)
        code2 = 'from mod1 import AClass\na_var = AClass()\n'
        mod2.write(code2)
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1, 'create')
        self.refactoring.undo()
        self.assertEquals(code1, mod1.read())
        self.assertEquals(code2, mod2.read())
    
    def test_using_on_an_occurance_outside_the_main_module(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod2, mod2.read().index('AClass') + 1, 'create')
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.AClass.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    def test_introduce_factory_in_nested_scopes(self):
        code = 'def create_var():\n'\
               '    class AClass(object):\n'\
               '        an_attr = 10\n'\
               '    return AClass()\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'def create_var():\n'\
                   '    class AClass(object):\n'\
                   '        an_attr = 10\n\n'\
                   '        @staticmethod\n        def create(*args, **kwds):\n'\
                   '            return AClass(*args, **kwds)\n'\
                   '    return AClass.create()\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_adding_factory_for_global_factories(self):
        code = 'class AClass(object):\n    an_attr = 10\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   'def create(*args, **kwds):\n' \
                   '    return AClass(*args, **kwds)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)
        self.assertEquals(expected, mod.read())

    @testutils.assert_raises(rope.base.exceptions.RefactoringException)
    def test_raising_exception_for_global_factory_for_nested_classes(self):
        code = 'def create_var():\n'\
               '    class AClass(object):\n'\
               '        an_attr = 10\n'\
               '    return AClass()\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)

    def test_changing_occurances_in_the_main_module_for_global_factories(self):
        code = 'class AClass(object):\n    an_attr = 10\na_var = AClass()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   'def create(*args, **kwds):\n' \
                   '    return AClass(*args, **kwds)\n'\
                   'a_var = create()'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_other_modules_for_global_factories(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1,
                                           'create', global_factory=True)
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                    'def create(*args, **kwds):\n' \
                    '    return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    def test_importing_if_necessary_in_other_modules_for_global_factories(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('from mod1 import AClass\npair = AClass(), AClass\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1,
                                           'create', global_factory=True)
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                    'def create(*args, **kwds):\n' \
                    '    return AClass(*args, **kwds)\n'
        expected2 = 'from mod1 import AClass\nimport mod1\npair = mod1.create(), AClass\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    # XXX: Should we replace `a_class` here with `AClass.create` too
    def test_changing_occurances_for_renamed_classes(self):
        code = 'class AClass(object):\n    an_attr = 10\na_class = AClass\na_var = a_class()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n' \
                   'a_class = AClass\n' \
                   'a_var = a_class()'
        self.refactoring.introduce_factory(mod, mod.read().index('a_class') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_transform_module_to_package(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod2)
        mod2 = self.project.get_resource('mod2')
        root_folder = self.project.get_root_folder()
        self.assertFalse(root_folder.has_child('mod2.py'))
        self.assertEquals('class AClass(object):\n    pass\n', root_folder.get_child('mod2').
                          get_child('__init__.py').read())

    def test_transform_module_to_package_undoing(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        self.refactoring.transform_module_to_package(mod)
        self.assertFalse(pkg.has_child('mod.py'))
        self.assertTrue(pkg.get_child('mod').has_child('__init__.py'))
        self.refactoring.undo()
        self.assertTrue(pkg.has_child('mod.py'))
        self.assertFalse(pkg.has_child('mod'))

    def test_transform_module_to_package_with_relative_imports(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod1)
        new_init = self.project.get_resource('pkg/mod1/__init__.py')
        self.assertEquals('import pkg.mod2\nfrom pkg.mod2 import AClass\n',
                          new_init.read())

class RefactoringUndoTest(unittest.TestCase):

    def setUp(self):
        super(RefactoringUndoTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.file = self.project.get_root_folder().create_file('file.txt')
        self.undo = Undo()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RefactoringUndoTest, self).tearDown()

    def test_simple_undo(self):
        change = ChangeContents(self.file, '1')
        change.do()
        self.assertEquals('1', self.file.read())
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('', self.file.read())

    def test_simple_redo(self):
        change = ChangeContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.undo.redo()
        self.assertEquals('1', self.file.read())

    def test_simple_re_undo(self):
        change = ChangeContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.undo.redo()
        self.undo.undo()
        self.assertEquals('', self.file.read())

    def test_multiple_undos(self):
        change = ChangeContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        change = ChangeContents(self.file, '2')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('1', self.file.read())
        change = ChangeContents(self.file, '3')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('1', self.file.read())
        self.undo.redo()
        self.assertEquals('3', self.file.read())


class EncapsulateFieldTest(unittest.TestCase):

    def setUp(self):
        super(EncapsulateFieldTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        self.mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        self.a_class = 'class A(object):\n    def __init__(self):\n        self.attr = 1\n'
        self.setter_and_getter = '\n    def get_attr(self):\n        return self.attr\n\n' \
                                 '    def set_attr(self, value):\n        self.attr = value\n'
        self.encapsulated = 'class A(object):\n    def __init__(self):\n        self.attr = 1\n\n' \
                            '    def get_attr(self):\n        return self.attr\n\n' \
                            '    def set_attr(self, value):\n        self.attr = value\n'

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(EncapsulateFieldTest, self).tearDown()

    def test_adding_getters_and_setters(self):
        code = self.a_class
        self.mod.write(code)
        self.refactoring.encapsulate_field(self.mod, code.index('attr') + 1)
        self.assertEquals(self.encapsulated, self.mod.read())

    def test_changing_getters_in_other_modules(self):
        self.mod1.write('import mod\na_var = mod.A()\nrange(a_var.attr)\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals('import mod\na_var = mod.A()\nrange(a_var.get_attr())\n',
                          self.mod1.read())

    def test_changing_setters_in_other_modules(self):
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr = 1\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals('import mod\na_var = mod.A()\na_var.set_attr(1)\n',
                          self.mod1.read())

    def test_changing_getters_in_setters(self):
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr = 1 + a_var.attr\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals(
            'import mod\na_var = mod.A()\na_var.set_attr(1 + a_var.get_attr())\n',
            self.mod1.read())
    
    def test_appending_to_class_end(self):
        self.mod1.write(self.a_class + 'a_var = A()\n')
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)
        self.assertEquals(self.encapsulated + 'a_var = A()\n',
                          self.mod1.read())

    def test_performing_in_other_modules(self):
        self.mod1.write('import mod\na_var = mod.A()\nrange(a_var.attr)\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)
        self.assertEquals(self.encapsulated, self.mod.read())
        self.assertEquals('import mod\na_var = mod.A()\nrange(a_var.get_attr())\n',
                          self.mod1.read())

    def test_changing_main_module_occurances(self):
        self.mod1.write(self.a_class + 'a_var = A()\na_var.attr = a_var.attr * 2\n')
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)
        self.assertEquals(
            self.encapsulated + 
            'a_var = A()\na_var.set_attr(a_var.get_attr() * 2)\n',
            self.mod1.read())

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_when_performed_on_non_attributes(self):
        self.mod1.write('attr = 10')
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_on_tuple_assignments(self):
        self.mod.write(self.a_class)
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr = 1\na_var.attr, b = 1, 2\n')
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_on_tuple_assignments2(self):
        self.mod.write(self.a_class)
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr = 1\nb, a_var.attr = 1, 2\n')
        self.refactoring.encapsulate_field(self.mod1, self.mod1.read().index('attr') + 1)

    def test_tuple_assignments_and_function_calls(self):
        self.mod1.write('import mod\ndef func(a1=0, a2=0):\n    pass\n'
                        'a_var = mod.A()\nfunc(a_var.attr, a2=2)\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals('import mod\ndef func(a1=0, a2=0):\n    pass\n'
                          'a_var = mod.A()\nfunc(a_var.get_attr(), a2=2)\n',
                          self.mod1.read())

    def test_tuple_assignments(self):
        self.mod1.write('import mod\na_var = mod.A()\na, b = a_var.attr, 1\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals(
            'import mod\na_var = mod.A()\na, b = a_var.get_attr(), 1\n',
            self.mod1.read())
    
    def test_changing_augmented_assignments(self):
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr += 1\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals(
            'import mod\na_var = mod.A()\na_var.set_attr(a_var.get_attr() + 1)\n',
            self.mod1.read())
    
    def test_changing_augmented_assignments2(self):
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr <<= 1\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals(
            'import mod\na_var = mod.A()\na_var.set_attr(a_var.get_attr() << 1)\n',
            self.mod1.read())
    

class LocalToFieldTest(unittest.TestCase):

    def setUp(self):
        super(LocalToFieldTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(LocalToFieldTest, self).tearDown()
    
    def test_simple_local_to_field(self):
        code = 'class A(object):\n    def a_func(self):\n' \
               '        var = 10\n'
        self.mod.write(code)
        self.refactoring.convert_local_variable_to_field(self.mod,
                                                         code.index('var') + 1)
        expected = 'class A(object):\n    def a_func(self):\n' \
                   '        self.var = 10\n'
        self.assertEquals(expected, self.mod.read())
    
    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_when_performed_on_a_global_var(self):
        self.mod.write('var = 10\n')
        self.refactoring.convert_local_variable_to_field(
            self.mod, self.mod.read().index('var') + 1)

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_when_performed_on_field(self):
        code = 'class A(object):\n    def a_func(self):\n' \
               '        self.var = 10\n'
        self.mod.write(code)
        self.refactoring.convert_local_variable_to_field(
            self.mod, self.mod.read().index('var') + 1)

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_when_performed_on_a_parameter(self):
        code = 'class A(object):\n    def a_func(self, var):\n' \
               '        a = var\n'
        self.mod.write(code)
        self.refactoring.convert_local_variable_to_field(
            self.mod, self.mod.read().index('var') + 1)

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_when_there_is_a_field_with_the_same_name(self):
        code = 'class A(object):\n    def __init__(self):\n        self.var = 1\n' \
               '    def a_func(self):\n        var = 10\n'
        self.mod.write(code)
        self.refactoring.convert_local_variable_to_field(
            self.mod, self.mod.read().rindex('var') + 1)

    def test_local_to_field_with_self_renamed(self):
        code = 'class A(object):\n    def a_func(myself):\n' \
               '        var = 10\n'
        self.mod.write(code)
        self.refactoring.convert_local_variable_to_field(self.mod,
                                                         code.index('var') + 1)
        expected = 'class A(object):\n    def a_func(myself):\n' \
                   '        myself.var = 10\n'
        self.assertEquals(expected, self.mod.read())
    
class IntroduceParameterTest(unittest.TestCase):

    def setUp(self):
        super(IntroduceParameterTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(IntroduceParameterTest, self).tearDown()
    
    def _introduce_parameter(self, offset, name):
        rope.refactor.introduce_parameter.IntroduceParameter(
            self.pycore, self.mod, offset).get_changes(name).do()
    
    def test_simple_case(self):
        self.mod.write('var = 1\ndef f():\n    b = var\n')
        offset = self.mod.read().rindex('var')
        self._introduce_parameter(offset, 'var')
        self.assertEquals('var = 1\ndef f(var=var):\n    b = var\n', self.mod.read())

    def test_changing_function_body(self):
        self.mod.write('var = 1\ndef f():\n    b = var\n')
        offset = self.mod.read().rindex('var')
        self._introduce_parameter(offset, 'p1')
        self.assertEquals('var = 1\ndef f(p1=var):\n    b = p1\n', self.mod.read())

    def test_unknown_variables(self):
        self.mod.write('def f():\n    b = var + c\n')
        offset = self.mod.read().rindex('var')
        self._introduce_parameter(offset, 'p1')
        self.assertEquals('def f(p1=var):\n    b = p1 + c\n', self.mod.read())

    @testutils.assert_raises(RefactoringException)
    def test_failing_when_not_inside(self):
        self.mod.write('var = 10\nb = var\n')
        offset = self.mod.read().rindex('var')
        self._introduce_parameter(offset, 'p1')

    def test_attribute_accesses(self):
        self.mod.write('class C(object):\n    a = 10\nc = C()\ndef f():\n    b = c.a\n')
        offset = self.mod.read().rindex('a')
        self._introduce_parameter(offset, 'p1')
        self.assertEquals('class C(object):\n    a = 10\nc = C()\ndef f(p1=c.a):\n    b = p1\n',
                          self.mod.read())

    def test_introducing_parameters_for_methods(self):
        self.mod.write('var = 1\nclass C(object):\n    def f(self):\n        b = var\n')
        offset = self.mod.read().rindex('var')
        self._introduce_parameter(offset, 'p1')
        self.assertEquals('var = 1\nclass C(object):\n    def f(self, p1=var):\n        b = p1\n',
                          self.mod.read())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ropetest.refactor.renametest.RenameRefactoringTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.extracttest.ExtractMethodTest))
    result.addTests(unittest.makeSuite(IntroduceFactoryTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.movetest.MoveRefactoringTest))
    result.addTests(unittest.makeSuite(RefactoringUndoTest))
    result.addTests(ropetest.refactor.inlinetest.suite())
    result.addTests(unittest.makeSuite(EncapsulateFieldTest))
    result.addTests(unittest.makeSuite(LocalToFieldTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.change_signature_test.ChangeSignatureTest))
    result.addTests(unittest.makeSuite(IntroduceParameterTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.importutilstest.ImportUtilsTest))
    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        unittest.main()
    else:
        runner = unittest.TextTestRunner()
        runner.run(suite())
