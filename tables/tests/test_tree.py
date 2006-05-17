import sys
import warnings
import unittest
import os
import tempfile

from tables import *
# Next imports are only necessary for this test suite
from tables import Group, Leaf, Table, Array

from common import verbose, heavy, cleanup
# To delete the internal attributes automagically
unittest.TestCase.tearDown = cleanup

# Test Record class
class Record(IsDescription):
    var1 = StringCol(length=4)    # 4-character String
    var2 = IntCol()               # integer
    var3 = Int16Col()             # short integer
    var4 = FloatCol()             # double (double-precision)
    var5 = Float32Col()           # float  (single-precision)

class TreeTestCase(unittest.TestCase):
    mode  = "w"
    title = "This is the table title"
    expectedrows = 10
    appendrows = 5

    def setUp(self):
        # Create a temporary file
        self.file = tempfile.mktemp(".h5")
        # Create an instance of HDF5 Table
        self.h5file = openFile(self.file, self.mode, self.title)
        self.populateFile()
        self.h5file.close()

    def populateFile(self):
        group = self.h5file.root
        maxshort = 1 << 15
        maxint   = 2147483647   # (2 ** 31 - 1)
        for j in range(3):
            # Create a table
            table = self.h5file.createTable(group, 'table'+str(j), Record,
                                        title = self.title,
                                        filters = None,
                                        expectedrows = self.expectedrows)
            # Get the record object associated with the new table
            d = table.row
            # Fill the table
            for i in xrange(self.expectedrows):
                d['var1'] = '%04d' % (self.expectedrows - i)
                d['var2'] = i
                d['var3'] = i % maxshort
                d['var4'] = float(i)
                d['var5'] = float(i)
                d.append()      # This injects the Record values
            # Flush the buffer for this table
            table.flush()

            # Create a couple of arrays in each group
            var1List = [ x['var1'] for x in table.iterrows() ]
            var4List = [ x['var4'] for x in table.iterrows() ]

            self.h5file.createArray(group, 'var1', var1List, "1")
            self.h5file.createArray(group, 'var4', var4List, "4")

            # Create a new group (descendant of group)
            group2 = self.h5file.createGroup(group, 'group'+str(j))
            # Iterate over this new group (group2)
            group = group2

    def tearDown(self):
        # Close the file
        if self.h5file.isopen:
            self.h5file.close()

        os.remove(self.file)
        cleanup(self)

    #----------------------------------------

    def test00_getNode(self):
        "Checking the File.getNode() with string node names"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_getNode..." % self.__class__.__name__

        self.h5file = openFile(self.file, "r")
        nodelist = ['/', '/table0', '/group0/var1', '/group0/group1/var4']
        nodenames = []
        for node in nodelist:
            object = self.h5file.getNode(node)
            nodenames.append(object._v_pathname)

        assert nodenames == nodelist
        if verbose:
            print "getNode(pathname) test passed"
        nodegroups = ['/', '/group0', '/group0/group1', '/group0/group1/group2']
        nodenames = ['var1', 'var4']
        nodepaths = []
        for group in nodegroups:
            for name in nodenames:
                try:
                    object = self.h5file.getNode(group, name)
                except LookupError:
                    pass
                else:
                    nodepaths.append(object._v_pathname)

        assert nodepaths == ['/var1', '/var4',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]

        if verbose:
            print "getNode(groupname, name) test passed"
        nodelist = ['/', '/group0', '/group0/group1', '/group0/group1/group2',
                    '/table0']
        nodenames = []
        groupobjects = []
        #warnings.filterwarnings("error", category=UserWarning)
        for node in nodelist:
            try:
                object = self.h5file.getNode(node, classname = 'Group')
            except LookupError:
                if verbose:
                    (type, value, traceback) = sys.exc_info()
                    print "\nGreat!, the next LookupError was catched!"
                    print value
            else:
                nodenames.append(object._v_pathname)
                groupobjects.append(object)

        assert nodenames == ['/', '/group0', '/group0/group1',
                             '/group0/group1/group2',
                             ]
        if verbose:
            print "getNode(groupname, classname='Group') test passed"

        # Reset the warning
        #warnings.filterwarnings("default", category=UserWarning)

        nodenames = ['var1', 'var4']
        nodearrays = []
        for group in groupobjects:
            for name in nodenames:
                try:
                    object = self.h5file.getNode(group, name, 'Array')
                except:
                    pass
                else:
                    nodearrays.append(object._v_pathname)

        assert nodearrays == ['/var1', '/var4',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]
        if verbose:
            print "getNode(groupobject, name, classname='Array') test passed"

    def test01_getNodeClass(self):
        "Checking the File.getNode() with instances"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test01_getNodeClass..." % self.__class__.__name__

        self.h5file = openFile(self.file, "r")
        # This tree ways of getNode usage should return a table instance
        table = self.h5file.getNode("/group0/table1")
        assert isinstance(table, Table)
        table = self.h5file.getNode("/group0", "table1")
        assert isinstance(table, Table)
        table = self.h5file.getNode(self.h5file.root.group0, "table1")
        assert isinstance(table, Table)

        # This should return an array instance
        arr = self.h5file.getNode("/group0/var1")
        assert isinstance(arr, Array)
        assert isinstance(arr, Leaf)

        # And this a Group
        group = self.h5file.getNode("/group0", "group1", "Group")
        assert isinstance(group, Group)

    def test02_listNodes(self):
        "Checking the File.listNodes() method"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02_listNodes..." % self.__class__.__name__

        # Made the warnings to raise an error
        #warnings.filterwarnings("error", category=UserWarning)
        self.h5file = openFile(self.file, "r")

        self.assertRaises(TypeError,
                          self.h5file.listNodes, '/', 'NoSuchClass')

        nodelist = ['/', '/group0', '/group0/table1', '/group0/group1/group2',
                    '/var1']
        nodenames = []
        objects = []
        for node in nodelist:
            try:
                objectlist = self.h5file.listNodes(node)
            except:
                pass
            else:
                objects.extend(objectlist)
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0', '/table0', '/var1', '/var4',
                             '/group0/group1', '/group0/table1',
                             '/group0/var1', '/group0/var4',
                             ]
        if verbose:
            print "listNodes(pathname) test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = self.h5file.listNodes(node)
            except:
                pass
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/group1', '/group0/table1',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/group2', '/group0/group1/table2',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]

        if verbose:
            print "listNodes(groupobject) test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = self.h5file.listNodes(node, 'Leaf')
            except TypeError:
                if verbose:
                    (type, value, traceback) = sys.exc_info()
                    print "\nGreat!, the next TypeError was catched!"
                    print value
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/table1',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/table2',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]

        if verbose:
            print "listNodes(groupobject, classname = 'Leaf') test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = self.h5file.listNodes(node, 'Table')
            except TypeError:
                if verbose:
                    (type, value, traceback) = sys.exc_info()
                    print "\nGreat!, the next TypeError was catched!"
                    print value
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/table1',
                             '/group0/group1/table2',
                             ]

        if verbose:
            print "listNodes(groupobject, classname = 'Table') test passed"

        # Reset the warning
        #warnings.filterwarnings("default", category=UserWarning)

    def test02b_iterNodes(self):
        "Checking the File.iterNodes() method"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test02b_iterNodes..." % self.__class__.__name__

        self.h5file = openFile(self.file, "r")

        self.assertRaises(TypeError,
                          self.h5file.listNodes, '/', 'NoSuchClass')

        nodelist = ['/', '/group0', '/group0/table1', '/group0/group1/group2',
                    '/var1']
        nodenames = []
        objects = []
        for node in nodelist:
            try:
                objectlist = [o for o in self.h5file.iterNodes(node)]
            except:
                pass
            else:
                objects.extend(objectlist)
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0', '/table0', '/var1', '/var4',
                             '/group0/group1', '/group0/table1',
                             '/group0/var1', '/group0/var4',
                             ]
        if verbose:
            print "iterNodes(pathname) test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = [o for o in self.h5file.iterNodes(node)]
            except:
                pass
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/group1', '/group0/table1',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/group2', '/group0/group1/table2',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]

        if verbose:
            print "iterNodes(groupobject) test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = [o for o in self.h5file.iterNodes(node, 'Leaf')]
            except TypeError:
                if verbose:
                    (type, value, traceback) = sys.exc_info()
                    print "\nGreat!, the next TypeError was catched!"
                    print value
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/table1',
                             '/group0/var1', '/group0/var4',
                             '/group0/group1/table2',
                             '/group0/group1/var1', '/group0/group1/var4',
                             ]

        if verbose:
            print "iterNodes(groupobject, classname = 'Leaf') test passed"

        nodenames = []
        for node in objects:
            try:
                objectlist = [o for o in self.h5file.iterNodes(node, 'Table')]
            except TypeError:
                if verbose:
                    (type, value, traceback) = sys.exc_info()
                    print "\nGreat!, the next TypeError was catched!"
                    print value
            else:
                for object in objectlist:
                    nodenames.append(object._v_pathname)

        assert nodenames == ['/group0/table1',
                             '/group0/group1/table2',
                             ]

        if verbose:
            print "iterNodes(groupobject, classname = 'Table') test passed"

        # Reset the warning
        #warnings.filterwarnings("default", category=UserWarning)

    def test03_TraverseTree(self):
        "Checking the File.walkGroups() method"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test03_TraverseTree..." % self.__class__.__name__

        self.h5file = openFile(self.file, "r")
        groups = []
        tables = []
        arrays = []
        for group in self.h5file.walkGroups():
            groups.append(group._v_pathname)
            for table in self.h5file.listNodes(group, 'Table'):
                tables.append(table._v_pathname)
            for arr in self.h5file.listNodes(group, 'Array'):
                arrays.append(arr._v_pathname)

        assert groups == ["/", "/group0", "/group0/group1",
                          "/group0/group1/group2"]

        assert tables == ["/table0", "/group0/table1", "/group0/group1/table2"]

        assert arrays == ['/var1', '/var4',
                          '/group0/var1', '/group0/var4',
                          '/group0/group1/var1', '/group0/group1/var4']
        if verbose:
            print "walkGroups() test passed"

        groups = []
        tables = []
        arrays = []
        for group in self.h5file.walkGroups("/group0/group1"):
            groups.append(group._v_pathname)
            for table in self.h5file.listNodes(group, 'Table'):
                tables.append(table._v_pathname)
            for arr in self.h5file.listNodes(group, 'Array'):
                arrays.append(arr._v_pathname)

        assert groups == ["/group0/group1",
                          "/group0/group1/group2"]

        assert tables == ["/group0/group1/table2"]

        assert arrays == ['/group0/group1/var1', '/group0/group1/var4']

        if verbose:
            print "walkGroups(pathname) test passed"

    def test04_walkNodes(self):
        "Checking File.walkNodes"

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test04_walkNodes..." % self.__class__.__name__

        self.h5file = openFile(self.file, "r")

        self.assertRaises(TypeError,
                          self.h5file.walkNodes('/', 'NoSuchClass').next)

        groups = []
        tables = []
        tables2 = []
        arrays = []
        for group in self.h5file.walkNodes(classname="Group"):
            groups.append(group._v_pathname)
            for table in group._f_walkNodes(classname='Table', recursive=0):
                tables.append(table._v_pathname)
        # Test the recursivity
        for table in self.h5file.root._f_walkNodes('Table', recursive=1):
            tables2.append(table._v_pathname)

        for arr in self.h5file.walkNodes(classname='Array'):
            arrays.append(arr._v_pathname)

        assert groups == ["/", "/group0", "/group0/group1",
                          "/group0/group1/group2"]
        assert tables == ["/table0", "/group0/table1",
                          "/group0/group1/table2"]
        assert tables2 == ["/table0", "/group0/table1",
                           "/group0/group1/table2"]
        assert arrays == ['/var1', '/var4',
                          '/group0/var1', '/group0/var4',
                          '/group0/group1/var1', '/group0/group1/var4']

        if verbose:
            print "File.__iter__() and Group.__iter__ test passed"

        groups = []
        tables = []
        arrays = []
        for group in self.h5file.walkNodes("/group0/group1", classname="Group"):
            groups.append(group._v_pathname)
            for table in group._f_walkNodes('Table'):
                tables.append(table._v_pathname)
            for arr in self.h5file.walkNodes(group, 'Array'):
                arrays.append(arr._v_pathname)

        assert groups == ["/group0/group1",
                          "/group0/group1/group2"]

        assert tables == ["/group0/group1/table2"]

        assert arrays == ['/group0/group1/var1', '/group0/group1/var4']

        if verbose:
            print "walkNodes(pathname, classname) test passed"


class DeepTreeTestCase(unittest.TestCase):
    """Checks for maximum deepest level in PyTables trees.

    Right now, the maximum depth for object tree is determined by the
    maximum recursion level offered by Python (which for my platform
    is a number between 768 and 1024).

    """
    def test00_deepTree(self):
        "Checking creation of large depth object tree Variable"

        # Here we put a more conservative limit to deal with more platforms
        # With maxdepth = 512 this test would take less than 20 MB
        # of main memory to run, which is quite reasonable nowadays.
        # With maxdepth = 1024 this test will take over 40 MB.
        if heavy:
            maxdepth = 1024  # Only for big machines!
        else:
            maxdepth = 256  # This should be safe for most machines

        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_deepTree..." % \
                  self.__class__.__name__
            print "Maximum depth tested :", maxdepth

        # Open a new empty HDF5 file
        file = tempfile.mktemp(".h5")
        #file = "deep.h5"
        fileh = openFile(file, mode = "w")
        #group = fileh.root
        pathname = "/"
        if verbose:
            print "Depth writing progress: ",
        # Iterate until maxdepth
        for depth in range(maxdepth):
            # Save it on the HDF5 file
            if verbose:
                print "%3d," % (depth),
            a = [1, 1]
            #fileh.createArray(group, 'array', a, "depth: %d" % depth)
            fileh.createArray(pathname, 'array', a, "depth: %d" % depth)
            #group = fileh.createGroup(group, 'group' + str(depth))
            group = fileh.createGroup(pathname, 'group' + str(depth))
            pathname = group._v_pathname
        # Close the file
        fileh.close()

        # Open the previous HDF5 file in read-only mode
        fileh = openFile(file, mode = "r")
        group = fileh.root
        pathname = "/"
        if verbose:
            print "\nDepth reading progress: ",
        # Get the metadata on the previosly saved arrays
        for depth in range(maxdepth):
            if verbose:
                print "%3d," % (depth),
            # Create an array for later comparison
            a = [1, 1]
            # Get the actual array
            b = group.array.read()
            # Arrays a and b must be equal
            assert a == b
            # Iterate over the next group
            group = fileh.getNode(pathname, 'group' + str(depth))
            #group = fileh.getNode(group, 'group' + str(depth))
            pathname = group._v_pathname
        if verbose:
            print # This flush the stdout buffer
        # Close the file
        fileh.close()

        # Then, delete the file
        os.remove(file)


class WideTreeTestCase(unittest.TestCase):
    """Checks for maximum number of children for a Group.
    """

    def test00_Leafs(self):
        """Checking creation of large number of leafs (1024) per group

        Variable 'maxchildren' controls this check. PyTables support
        up to 4096 children per group, but this would take too much
        memory (up to 64 MB) for testing purposes (may be we can add a
        test for big platforms). A 1024 children run takes up to 30 MB.
        A 512 children test takes around 25 MB.
        """

        import time
        if heavy:
            maxchildren = 4096
        else:
            maxchildren = 256
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_wideTree..." % \
                  self.__class__.__name__
            print "Maximum number of children tested :", maxchildren
        # Open a new empty HDF5 file
        file = tempfile.mktemp(".h5")
        #file = "test_widetree.h5"

        a = [1, 1]
        fileh = openFile(file, mode = "w")
        if verbose:
            print "Children writing progress: ",
        for child in range(maxchildren):
            if verbose:
                print "%3d," % (child),
            fileh.createArray(fileh.root, 'array' + str(child),
                              a, "child: %d" % child)
        if verbose:
            print
        # Close the file
        fileh.close()

        t1 = time.time()
        a = [1, 1]
        # Open the previous HDF5 file in read-only mode
        fileh = openFile(file, mode = "r")
        if verbose:
            print "\nTime spent opening a file with %d arrays: %s s" % \
                  (maxchildren, time.time()-t1)
            print "\nChildren reading progress: ",
        # Get the metadata on the previosly saved arrays
        for child in range(maxchildren):
            if verbose:
                print "%3d," % (child),
            # Create an array for later comparison
            # Get the actual array
            array_ = getattr(fileh.root, 'array' + str(child))
            b = array_.read()
            # Arrays a and b must be equal
            assert a == b
        if verbose:
            print # This flush the stdout buffer
        # Close the file
        fileh.close()
        # Then, delete the file
        os.remove(file)


    def test01_wideTree(self):
        """Checking creation of large number of groups (1024) per group

        Variable 'maxchildren' controls this check. PyTables support
        up to 4096 children per group, but this would take too much
        memory (up to 64 MB) for testing purposes (may be we can add a
        test for big platforms). A 1024 children run takes up to 30 MB.
        A 512 children test takes around 25 MB.
        """

        import time
        if heavy:
            # for big platforms!
            maxchildren = 4096
        else:
            # for standard platforms
            maxchildren = 256
        if verbose:
            print '\n', '-=' * 30
            print "Running %s.test00_wideTree..." % \
                  self.__class__.__name__
            print "Maximum number of children tested :", maxchildren
        # Open a new empty HDF5 file
        file = tempfile.mktemp(".h5")
        #file = "test_widetree.h5"

        fileh = openFile(file, mode = "w")
        if verbose:
            print "Children writing progress: ",
        for child in range(maxchildren):
            if verbose:
                print "%3d," % (child),
            fileh.createGroup(fileh.root, 'group' + str(child),
                              "child: %d" % child)
        if verbose:
            print
        # Close the file
        fileh.close()

        t1 = time.time()
        # Open the previous HDF5 file in read-only mode
        fileh = openFile(file, mode = "r")
        if verbose:
            print "\nTime spent opening a file with %d groups: %s s" % \
                  (maxchildren, time.time()-t1)
            print "\nChildren reading progress: ",
        # Get the metadata on the previosly saved arrays
        for child in range(maxchildren):
            if verbose:
                print "%3d," % (child),
            # Get the actual group
            group = getattr(fileh.root, 'group' + str(child))
            # Arrays a and b must be equal
            assert group._v_title == "child: %d" % child
        if verbose:
            print # This flush the stdout buffer
        # Close the file
        fileh.close()
        # Then, delete the file
        os.remove(file)



class HiddenTreeTestCase(unittest.TestCase):

    """Check for hidden groups, leaves and hierarchies."""

    def setUp(self):
        self.h5fname = tempfile.mktemp('.h5')
        self.h5file = openFile(
            self.h5fname, 'w', title = "Test for hidden nodes")

        self.visible = []  # list of visible object paths
        self.hidden = []  # list of hidden object paths

        # Create some visible nodes: a, g, g/a1, g/a2, g/g, g/g/a.
        h5f = self.h5file
        a = h5f.createArray('/', 'a', [0]);
        g = h5f.createGroup('/', 'g');
        g_a1 = h5f.createArray(g, 'a1', [0]);
        g_a2 = h5f.createArray(g, 'a2', [0]);
        g_g = h5f.createGroup(g, 'g');
        g_g_a = h5f.createArray(g_g, 'a', [0]);

        self.visible.extend(['/a', '/g', '/g/a1', '/g/a2', '/g/g', '/g/g/a'])

        # Create some hidden nodes: _p_a, _p_g, _p_g/a, _p_g/_p_a, g/_p_a.
        ha = h5f.createArray('/', '_p_a', [0]);
        hg = h5f.createGroup('/', '_p_g');
        hg_a = h5f.createArray(hg, 'a', [0]);
        hg_ha = h5f.createArray(hg, '_p_a', [0]);
        g_ha = h5f.createArray(g, '_p_a', [0]);

        self.hidden.extend(
            ['/_p_a', '/_p_g', '/_p_g/a', '/_p_g/_p_a', '/g/_p_a'])


    def tearDown(self):
        self.h5file.close()
        self.h5file = None
        os.remove(self.h5fname)


    def test00_objects(self):
        """Absence of hidden nodes in `File.objects`."""

        objects = self.h5file.objects

        warnings.filterwarnings('ignore', category=DeprecationWarning)

        for vpath in self.visible:
            self.assert_(vpath in objects,
                         "Missing visible node ``%s`` from ``File.objects``." % vpath)
        for hpath in self.hidden:
            self.assert_(hpath not in objects,
                         "Found hidden node ``%s`` in ``File.objects``." % hpath)

        warnings.filterwarnings('default', category=DeprecationWarning)


    def test00b_objects(self):
        """Object dictionaries conformance with ``walkNodes()``."""

        def dictCheck(dictName, className):
            file_ = self.h5file

            objects = getattr(file_, dictName)
            walkPaths = [node._v_pathname
                         for node in file_.walkNodes('/', className)]
            dictPaths = [path for path in objects]
            walkPaths.sort()
            dictPaths.sort()
            self.assertEqual(
                walkPaths, dictPaths,
                "nodes in ``%s`` do not match those from ``walkNodes()``"
                % dictName)
            self.assertEqual(
                len(walkPaths), len(objects),
                "length of ``%s`` differs from that of ``walkNodes()``"
                % dictName)

        warnings.filterwarnings('ignore', category=DeprecationWarning)

        dictCheck('objects', None)
        dictCheck('groups', 'Group')
        dictCheck('leaves', 'Leaf')

        warnings.filterwarnings('default', category=DeprecationWarning)


    def test01_getNode(self):
        """Node availability via `File.getNode()`."""

        h5f = self.h5file

        for vpath in self.visible:
            node = h5f.getNode(vpath)
        for hpath in self.hidden:
            node = h5f.getNode(hpath)


    def test02_walkGroups(self):
        """Hidden group absence in `File.walkGroups()`."""

        hidden = self.hidden

        for group in self.h5file.walkGroups('/'):
            pathname = group._v_pathname
            self.assert_(pathname not in hidden,
                         "Walked across hidden group ``%s``." % pathname)


    def test03_walkNodes(self):
        """Hidden node absence in `File.walkNodes()`."""

        hidden = self.hidden

        for node in self.h5file.walkNodes('/'):
            pathname = node._v_pathname
            self.assert_(pathname not in hidden,
                         "Walked across hidden node ``%s``." % pathname)


    def test04_listNodesVisible(self):
        """Listing visible nodes under a visible group (listNodes)."""

        hidden = self.hidden

        for node in self.h5file.listNodes('/g'):
            pathname = node._v_pathname
            self.assert_(pathname not in hidden,
                         "Listed hidden node ``%s``." % pathname)


    def test04b_listNodesVisible(self):
        """Listing visible nodes under a visible group (iterNodes)."""

        hidden = self.hidden

        for node in self.h5file.iterNodes('/g'):
            pathname = node._v_pathname
            self.assert_(pathname not in hidden,
                         "Listed hidden node ``%s``." % pathname)


    def test05_listNodesHidden(self):
        """Listing visible nodes under a hidden group (listNodes)."""

        hidden = self.hidden

        node_to_find = '/_p_g/a'
        found_node = False
        for node in self.h5file.listNodes('/_p_g'):
            pathname = node._v_pathname
            if pathname == node_to_find:
                found_node = True
            self.assert_(pathname in hidden,
                         "Listed hidden node ``%s``." % pathname)

        self.assert_(found_node,
                     "Hidden node ``%s`` was not listed." % node_to_find)


    def test05b_iterNodesHidden(self):
        """Listing visible nodes under a hidden group (iterNodes)."""

        hidden = self.hidden

        node_to_find = '/_p_g/a'
        found_node = False
        for node in self.h5file.iterNodes('/_p_g'):
            pathname = node._v_pathname
            if pathname == node_to_find:
                found_node = True
            self.assert_(pathname in hidden,
                         "Listed hidden node ``%s``." % pathname)

        self.assert_(found_node,
                     "Hidden node ``%s`` was not listed." % node_to_find)


    def test06_reopen(self):
        """Reopening a file with hidden nodes."""

        self.h5file.close()
        self.h5file = openFile(self.h5fname)
        self.test00_objects()


    def test07_move(self):
        """Moving a node between hidden and visible groups."""

        isVisibleNode = self.h5file.isVisibleNode

        self.assert_(not isVisibleNode('/_p_g/a'))
        self.h5file.moveNode('/_p_g/a', '/g', 'a')
        self.assert_(isVisibleNode('/g/a'))
        self.h5file.moveNode('/g/a', '/_p_g', 'a')
        self.assert_(not isVisibleNode('/_p_g/a'))


    def test08_remove(self):
        """Removing a visible group with hidden children."""

        self.assert_('/g/_p_a' in self.h5file)
        self.h5file.root.g._f_remove(recursive=True)
        self.assert_('/g/_p_a' not in self.h5file)



#----------------------------------------------------------------------

def suite():
    theSuite = unittest.TestSuite()
    # This counter is useful when detecting memory leaks
    niter = 1
    #heavy=1

    #theSuite.addTest(unittest.makeSuite(DeepTreeTestCase))
    for i in range(niter):
        theSuite.addTest(unittest.makeSuite(TreeTestCase))
        theSuite.addTest(unittest.makeSuite(DeepTreeTestCase))
        theSuite.addTest(unittest.makeSuite(WideTreeTestCase))
        theSuite.addTest(unittest.makeSuite(HiddenTreeTestCase))

    return theSuite


if __name__ == '__main__':
    unittest.main( defaultTest='suite' )