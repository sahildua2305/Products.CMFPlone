from OFS.PropertyManager import PropertyManager
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import CMFCorePermissions
from Products.CMFCore.Expression import Expression
from Products.CMFPlone.migrations.migration_util import safeEditProperty

from zLOG import INFO, ERROR
from SetupBase import SetupWidget

def modifyAuthentication(self, portal):
    #set up cookie crumbler
    cookie_authentication = getToolByName(portal, 'cookie_authentication')
    cookie_authentication._updateProperty('auto_login_page', 'require_login')

def installPortalTools(self,portal):
    ''' thats the place to install custom tools '''
    pass

def addSiteProperties(self, portal):
    """ adds site_properties in portal_properties """
    id='site_properties'
    title='Site wide properties'
    p=PropertyManager('id')
    if id not in portal.portal_properties.objectIds():
        portal.portal_properties.addPropertySheet(id, title, p)
    p=getattr(portal.portal_properties, id)

    if not hasattr(p,'allowAnonymousViewAbout'):
        safeEditProperty(p, 'allowAnonymousViewAbout', 1, 'boolean')
    if not hasattr(p,'localTimeFormat'):
        safeEditProperty(p, 'localTimeFormat', '%Y-%m-%d', 'string')
    if not hasattr(p,'localLongTimeFormat'):
        safeEditProperty(p, 'localLongTimeFormat', '%Y-%m-%d %I:%M %p', 'string')
    if not hasattr(p,'default_language'):
        safeEditProperty(p, 'default_language', 'en', 'string')
    if not hasattr(p,'default_charset'):
        safeEditProperty(p, 'default_charset', 'utf-8', 'string')
    if not hasattr(p,'use_folder_tabs'):
        safeEditProperty(p, 'use_folder_tabs',('Folder',), 'lines')
    if not hasattr(p,'use_folder_contents'):
        safeEditProperty(p, 'use_folder_contents',('Folder',), 'lines')
    if not hasattr(p,'ext_editor'):
        safeEditProperty(p, 'ext_editor', 0, 'boolean')
    if not hasattr(p, 'available_editors'):
        safeEditProperty(p, 'available_editors', ('None', ), 'lines')
    if not hasattr(p, 'allowRolesToAddKeywords'):
        safeEditProperty(p, 'allowRolesToAddKeywords', ['Manager', 'Reviewer'], 'lines')
    if not hasattr(p,'allow_sendto'):
        safeEditProperty(p, 'allow_sendto', 0, 'boolean')        

def setupDefaultLeftRightSlots(self, portal):
    """ sets up the slots on objectmanagers """
    left_slots=( 'here/navigation_tree_slot/macros/navigationBox'
               , 'here/login_slot/macros/loginBox'
               , 'here/related_slot/macros/relatedBox' )
    right_slots=( 'here/workflow_review_slot/macros/review_box'
                , 'here/news_slot/macros/newsBox'
                , 'here/events_slot/macros/eventsBox' 
                , 'here/recently_published_slot/macros/recentlyPublishedBox' 
                , 'here/calendar_slot/macros/calendarBox' )
    safeEditProperty(portal, 'left_slots', left_slots, 'lines')
    safeEditProperty(portal, 'right_slots', right_slots, 'lines')
    safeEditProperty(portal.Members, 'right_slots', (), 'lines')

def setupDefaultItemActionSlots(self, portal):                
    """ Sets up the default action item slots """
    item_action_slots=( 'here/actions_slot/macros/print'
                      , 'here/actions_slot/macros/sendto'
          , 'here/actions_slot/macros/syndication' )
    safeEditProperty(portal, 'item_action_slots', item_action_slots, 'lines')

def installExternalEditor(self, portal):
    ''' responsible for doing whats necessary if external editor is found '''
    types_tool=getToolByName(portal, 'portal_types')
    methods=('PUT', 'manage_FTPget')
    exclude=('Topic', 'Event', 'Folder')
    for ctype in types_tool.objectValues():
        if ctype.getId() not in exclude:
            ctype.addAction( 'external_edit',
                            name='External Edit',
                            action='external_edit',
                            condition='',
                            permission=CMFCorePermissions.ModifyPortalContent,
                            category='object',
                            visible=0 )
    from Products.ExternalEditor.ExternalEditor import ExternalEditorPermission
    portal.manage_permission(ExternalEditorPermission, ('Manager', 'Authenticated'), acquire=0)

def assignTitles(self, portal):
    titles={'portal_actions':'Contains custom tabs and buttons',
     'portal_membership':'Handles membership policies',
     'portal_memberdata':'Handles the available properties on Members',
     'portal_undo':'Defines actions and functionality related to undo',
     'portal_types':'Controls the available Content Types in your portal',
     'plone_utils':'Various Plone Utility methods',
     'portal_navigation':'Responsible for redirecting to the right page in forms',
     'portal_metadata':'Controls metadata - like keywords, copyrights etc',
     'portal_migration':'Handles migrations to newer Plone versions',
     'portal_registration':'Handles registration of new users',
     'portal_skins':'Controls skin behaviour (search order etc)',
     'portal_syndication':'Generates RSS for folders',
     'portal_workflow':'Contains workflow definitions for your portal',
     'portal_url':'Methods to anchor you to the root of your Plone site',
     'portal_form':'Used together with templates to do validation and navigation',
     'portal_discussion':'Controls how discussions are stored by default on content',
     'portal_catalog':'Indexes all content in the site',
     'portal_form_validation':'Deprecated, not in use',
     'portal_factory':'Responsible for the creation of content objects',
     'portal_calendar':'Controls how Events are shown'
     }

    for o in portal.objectValues():
        title=titles.get(o.getId(), None)
        if title:
            o.title=title

def addMemberdata(self, portal):
    md=getToolByName(portal, 'portal_memberdata')
    if not hasattr(md,'formtooltips'):
        safeEditProperty(md, 'formtooltips', '1', 'boolean')
    if not hasattr(md,'visible_ids'):
        safeEditProperty(md, 'visible_ids', '1', 'boolean')
    if not hasattr(md,'wysiwyg_editor'):
        safeEditProperty(md, 'wysiwyg_editor', '', 'string')
    if not hasattr(md,'listed'):
        safeEditProperty(md, 'listed', '1', 'boolean')
    else:
        safeEditProperty(md, 'listed','1')
    if not hasattr(md, 'fullname'):
        safeEditProperty(md, 'fullname', '', 'string')

def modifyActionProviders(self, portal):
    mt=getToolByName(portal, 'portal_properties')
    _actions=mt._cloneActions()
    for action in _actions:
        if action.id=='configPortal':
            action.title='Setup Plone'
    mt._actions=_actions

    at=getToolByName(portal, 'portal_actions')
    _actions=at._cloneActions()
    for action in _actions:
        if action.id=='folderContents':
            action.title='Contents'
            action.name='Contents'
    at._actions=_actions
    
def modifyMembershipTool(self, portal):
    mt=getToolByName(portal, 'portal_membership')
    mt.addAction('myworkspace'
                ,'My Workspace'
                ,'python: portal.portal_membership.getHomeUrl()+"/workspace"'
                ,'python: member and portal.portal_membership.getHomeFolder()'
                ,'View'
                ,'user'
                , visible=0)
    new_actions=[]
    for a in mt._cloneActions():
        if a.id=='login':
            a.title='Log in'
        if a.id=='logout':
            a.title='Log out'
        if a.id=='preferences':
            a.title='My Preferences'
            a.action=Expression('string:${portal_url}/portal_form/personalize_form')
            new_actions.insert(0, a)
        if a.id in ('addFavorite', 'favorites'):
            a.visible=0
            new_actions.insert(1,a)
        if a.id=='mystuff':
            a.title='My Folder'
            new_actions.insert(0, a)
        elif a.id=='myworkspace':
            new_actions.insert(1, a)
        elif a.id=='logout':
            new_actions.append(a)
        else:
            new_actions.insert(len(new_actions)-1,a)
    mt._actions=new_actions

def modifySkins(self, portal):
    #remove non Plone skins from skins tool
    #since we implemented the portal_form proxy these skins will no longer work
    
    # this should be run through the skins setup widget :)
    st=getToolByName(portal, 'portal_skins')
    skins_map=st._getSelections()
    if skins_map.has_key('No CSS'):
        del skins_map['No CSS']
    if skins_map.has_key('Nouvelle'):        
        del skins_map['Nouvelle']
    if skins_map.has_key('Basic'):        
        del skins_map['Basic']
    st.selections=skins_map
    
    types=getToolByName(portal, 'portal_types')
    for t in types.objectValues():
        _actions=t._cloneActions()
        for a in _actions:
            if a.id == 'metadata':
                a.name = 'Properties'   #1.3
                a.title = 'Properties'  #1.4
            if a.id == 'local_roles':
                a.name = 'Sharing'
                a.title = 'Sharing'
            if a.id == 'content_status_history':
                a.visible = 0
        t._actions=_actions
            
def addNewActions(self, portal):
    at=getToolByName(portal, 'portal_actions')

    at.addAction('index_html',
                 name='Home',
                 action='string:$portal_url',
                 condition='',
                 permission='View',
                 category='portal_tabs')
    at.addAction('news',
                 name='News',
                 action='string:$portal_url/news',
                 condition='',
                 permission='View',
                 category='portal_tabs')
    at.addAction('Members',
                 name='Members',
                 action='python:portal.portal_membership.getMembersFolder().absolute_url()',
                 condition='python:portal.portal_membership.getMembersFolder()',
                 permission='View',
                 category='portal_tabs')

    #This is now a drop down.
    #at.addAction('content_status_history',
    #             name='State',
    #             action='string:${object_url}/content_status_history',
    #             condition='python:object and portal.portal_workflow.getTransitionsFor(object, object.getParentNode())',
    #             permission='View',
    #             category='object_tabs' )

    at.addAction('change_ownership',
                 name='Ownership',
                 action='string:${object_url}/ownership_form',
                 condition='',
                 permission=CMFCorePermissions.ManagePortal,
                 category='object_tabs',
                 visible=0)
    at.addAction('rename',
                 name='Rename',
                 action='string:folder_rename_form:method',
                 condition='',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')
    at.addAction('cut',
                 name='Cut',
                 action='string:folder_cut:method',
                 condition='',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')
    at.addAction('copy',
                 name='Copy',
                 action='string:folder_copy:method',
                 condition='',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')
    at.addAction('paste',
                 name='Paste',
                 action='string:folder_paste:method',
                 condition='folder/cb_dataValid',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')
    at.addAction('delete',
                 name='Delete',
                 action='string:folder_delete:method',
                 condition='',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')
    at.addAction('change_status',
                 name='Change Status',
                 action='string:content_status_history:method',
                 condition='',
                 permission=CMFCorePermissions.ModifyPortalContent,
                 category='folder_buttons')

functions = {
    'addSiteProperties': addSiteProperties,
    'setupDefaultLeftRightSlots': setupDefaultLeftRightSlots,
    'setupDefaultItemActionSlots': setupDefaultItemActionSlots,
    'installExternalEditor': installExternalEditor,
    'assignTitles': assignTitles,
    'addMemberdata': addMemberdata,
    'modifyMembershipTool': modifyMembershipTool,
    'addNewActions': addNewActions,
    'modifySkins': modifySkins,
    'installPortalTools': installPortalTools,
    'modifyAuthentication': modifyAuthentication,
    'modifyActionProviders': modifyActionProviders,
    }

class GeneralSetup(SetupWidget):
    type = 'General Setup'
   
    description = """This applies a function to the site. These functions are some of the basic 
set up features of a site. The chances are you will not want to apply these again. <b>Please note</b> 
these functions do not have a uninstall function."""
    
    def setup(self):
        pass
    
    def delItems(self, fns):
        out = []          
        out.append(('Currently there is no way to remove a function', INFO))
        return out

    def addItems(self, fns):   
        out = []         
        for fn in fns:
            functions[fn](self, self.portal)
            out.append(('Function %s has been applied' % fn, INFO))
        return out

    def installed(self):
        return []
        
    def available(self):
        """ Go get the functions """
        return functions.keys()
    
