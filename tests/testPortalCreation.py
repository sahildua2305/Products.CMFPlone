#
# Tests portal creation
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase
from Products.CMFPlone.tests import dummy

from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from OFS.SimpleItem import SimpleItem
from Acquisition import aq_base


class TestPortalCreation(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        self.membership = self.portal.portal_membership
        self.workflow = self.portal.portal_workflow

    def testPloneSkins(self):
        # Plone skins should have been set up
        self.failUnless(hasattr(self.folder, 'plone_powered.gif'))

    def testDefaultView(self):
        # index_html should render
        self.portal.index_html()

    def testWorkflowIsActionProvider(self):
        # XXX: This change has been backed out and the test inverted!
        # Remove portal_workflow by default.  We are falling back to
        # our use of the 'review_slot'.  There are no places using
        # the worklist ui anymore directly from the listFilteredActionsFor
        at = self.portal.portal_actions
        self.failUnless('portal_workflow' in at.listActionProviders())

    def testReplyTabIsOff(self):
        # Ensure 'reply' tab is turned off
        # XXX NOTE: ActionProviderBAse should have a 'getActionById'
        # that does this for x in: if x == id
        dt_actions = self.portal.portal_discussion.listActions()
        reply_visible=1
        for action in dt_actions:
            if action.id=='reply':
                reply_visible=action.visible
        self.assertEqual(reply_visible, 0)

    def testLargePloneFolderWorkflow(self):
        # Large Plone Folder should use folder_workflow
        # http://plone.org/collector/2744
        lpf_chain = self.workflow.getChainFor('Large Plone Folder')
        self.failUnless('folder_workflow' in lpf_chain)
        self.failIf('plone_workflow' in lpf_chain)


class TestPortalBugs(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        self.membership = self.portal.portal_membership
        self.members = self.membership.getMembersFolder()
        # Fake the Members folder contents
        self.members._setObject('index_html', ZopePageTemplate('index_html'))

    def testMembersIndexHtml(self):
        # index_html for Members folder should be a Page Template
        members = self.members
        self.assertEqual(aq_base(members).meta_type, 'Large Plone Folder')
        self.failUnless(hasattr(aq_base(members), 'index_html'))
        # getitem works
        self.assertEqual(aq_base(members)['index_html'].meta_type, 'Page Template')
        self.assertEqual(members['index_html'].meta_type, 'Page Template')
        # _getOb works
        self.assertEqual(aq_base(members)._getOb('index_html').meta_type, 'Page Template')
        self.assertEqual(members._getOb('index_html').meta_type, 'Page Template')
        # getattr works when called explicitly
        self.assertEqual(aq_base(members).__getattr__('index_html').meta_type, 'Page Template')
        self.assertEqual(members.__getattr__('index_html').meta_type, 'Page Template')

    def testLargePloneFolderHickup(self):
        # Attribute access for 'index_html' acquired the Document from the
        # portal instead of returning the local Page Template. This was due to
        # special treatment of 'index_html' in the PloneFolder base class and
        # got fixed by hazmat.
        members = self.members
        self.assertEqual(aq_base(members).meta_type, 'Large Plone Folder')
        #self.assertEqual(members.index_html.meta_type, 'Document')
        self.assertEqual(members.index_html.meta_type, 'Page Template')

    def testManageBeforeDeleteIsCalledRecursively(self):
        # When the portal is deleted, all subobject should have
        # their manage_beforeDelete hook called. Fixed by geoffd.
        self.folder._setObject('foo', dummy.Item())
        self.foo = self.folder.foo
        self.app._delObject(PloneTestCase.portal_name)
        self.failUnless(self.foo.manage_before_delete_called)


class TestManagementPageCharset(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        self.properties = self.portal.portal_properties

    def testManagementPageCharsetEqualsDefaultCharset(self):
        # Checks that 'management_page_charset' attribute of the portal
        # reflects 'portal_properties/site_properties/default_charset'.
        default_charset = self.properties.site_properties.getProperty('default_charset', None) 
        self.failUnless(default_charset)
        manage_charset = getattr(self.portal, 'management_page_charset', None)
        self.failUnless(manage_charset)
        self.assertEqual(manage_charset, default_charset)
        self.assertEqual(manage_charset, 'utf-8')
        
    def testManagementPageCharsetIsComputedAttribute(self):
        # Checks that 'management_page_charset' attribute of the portal
        # is a ComputedAttribute and always follows the default_charset property.
        self.properties.site_properties.manage_changeProperties(default_charset='latin1')
        default_charset = self.properties.site_properties.getProperty('default_charset', None) 
        manage_charset = getattr(self.portal, 'management_page_charset', None)
        self.assertEqual(manage_charset, default_charset)
        self.assertEqual(manage_charset, 'latin1')

    def testManagementPageCharsetFallbackNoProperty(self):
        self.properties.site_properties._delProperty('default_charset')
        manage_charset = getattr(self.portal, 'management_page_charset', None)
        self.assertEqual(manage_charset, 'utf-8')

    def testManagementPageCharsetFallbackNoPropertySheet(self):
        self.properties._delObject('site_properties')
        manage_charset = getattr(self.portal, 'management_page_charset', None)
        self.assertEqual(manage_charset, 'utf-8')

    def testManagementPageCharsetFallbackNoPropertyTool(self):
        self.portal._delObject('portal_properties')
        manage_charset = getattr(self.portal, 'management_page_charset', None)
        self.assertEqual(manage_charset, 'utf-8')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPortalCreation))
    suite.addTest(makeSuite(TestPortalBugs))
    suite.addTest(makeSuite(TestManagementPageCharset))
    return suite

if __name__ == '__main__':
    framework()
