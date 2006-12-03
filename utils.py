import re
from types import ClassType
from os.path import join, abspath, split
from cStringIO import StringIO

from PIL import Image

import zope.interface
from zope.interface import implementedBy
from zope.component import getMultiAdapter
from zope.component.interfaces import ComponentLookupError

import OFS
import Globals
from Acquisition import aq_base, aq_inner, aq_parent
from DateTime import DateTime
from Products.Five import BrowserView as BaseView
from Products.Five.bridge import fromZ2Interface
from Products.CMFCore.utils import ToolInit as CMFCoreToolInit
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.UnicodeNormalizer import normalizeUnicode
from Products.CMFPlone.interfaces.Translatable import ITranslatable
from Products.CMFPlone import PloneMessageFactory as _
import transaction

# Canonical way to get at CMFPlone directory
PACKAGE_HOME = Globals.package_home(globals())
WWW_DIR = join(PACKAGE_HOME, 'www')

# Log methods
from log import log
from log import log_exc
from log import log_deprecated

# Define and compile static regexes
IGNORE_REGEX = re.compile(r"[']")
FILENAME_REGEX = re.compile(r"^(.+)\.(\w{,4})$")
NON_WORD_REGEX = re.compile(r"[\W\-]+")
DANGEROUS_CHARS_REGEX = re.compile(r"[?&/:\\#]+")
EXTRA_DASHES_REGEX = re.compile(r"(^\-+)|(\-+$)")

# Settings for member image resize quality
PIL_SCALING_ALGO = Image.ANTIALIAS
PIL_QUALITY = 88
MEMBER_IMAGE_SCALE = (75, 100)
IMAGE_SCALE_PARAMS = {'scale': MEMBER_IMAGE_SCALE,
                      'quality': PIL_QUALITY,
                      'algorithm': PIL_SCALING_ALGO,
                      'default_format': 'PNG'}

_marker = []

class BrowserView(BaseView):

    def __init__(self, context, request):
        self.context = [context]
        self.request = request

def parent(obj):
    return aq_parent(aq_inner(obj))

def context(view):
    return view.context[0]

def createBreadCrumbs(context, request):
    view = getMultiAdapter((context, request), name='breadcrumbs_view')
    return view.breadcrumbs()

def createNavTree(context, request, sitemap=False):
    view = getMultiAdapter((context, request), name='navtree_builder_view')
    return view.navigationTree()

def createSiteMap(context, request, sitemap=False):
    view = getMultiAdapter((context, request), name='sitemap_builder_view')
    return view.siteMap()

def _getDefaultPageView(obj, request):
    """This is a nasty hack because the view lookup fails when it occurs too
       early in the publishing process because the request isn't marked with
       the default skin.  Explicitly marking the request appears to cause
       connection errors, so we just instantiate the view manually.
    """
    try:
        view = getMultiAdapter((obj, request), name='default_page')
    except ComponentLookupError:
        # XXX: import here to avoid a circular dependency
        from browser.navigation import DefaultPage
        view = DefaultPage(obj, request)
    return view

def isDefaultPage(obj, request, context=None):
    container = parent(obj)
    if container is None:
        return False
    view = _getDefaultPageView(container, request)
    if context is None:
        context = obj
    return view.isDefaultPage(obj, context)

def getDefaultPage(obj, request, context=None):
    # Short circuit if we are not looking at a Folder
    if not obj.isPrincipiaFolderish:
        return None
    view = _getDefaultPageView(obj, request)
    if context is None:
        context = obj
    return view.getDefaultPage(context)

def isIDAutoGenerated(context, id):
    # In 2.1 non-autogenerated is the common case, caught exceptions are
    # expensive, so let's make a cheap check first
    if id.count('.') != 2:
        return False

    pt = getToolByName(context, 'portal_types')
    portaltypes = pt.listContentTypes()
    portaltypes.extend([pt.lower() for pt in portaltypes])

    try:
        obj_type, date_created, random_number = id.split('.')
        type = ' '.join(obj_type.split('_'))
        # New autogenerated ids may have a lower case portal type
        if ((type in portaltypes or obj_type in portaltypes) and
            DateTime(date_created) and
            float(random_number)):
            return True
    except (ValueError, AttributeError, IndexError, DateTime.DateTimeError):
        pass

    return False

def lookupTranslationId(obj, page, ids):
    implemented = ITranslatable.isImplementedBy(obj)
    if not implemented or implemented and not obj.isTranslation():
        pageobj = getattr(obj, page, None)
        if (pageobj is not None and
            ITranslatable.isImplementedBy(pageobj)):
            translation = pageobj.getTranslation()
            if (translation is not None and
                ids.has_key(translation.getId())):
                page = translation.getId()
    return page

def pretty_title_or_id(context, obj, empty_value=_marker):
    """Return the best possible title or id of an item, regardless
       of whether obj is a catalog brain or an object, but returning an
       empty title marker if the id is not set (i.e. it's auto-generated).
    """
    #if safe_hasattr(obj, 'aq_explicit'):
    #    obj = obj.aq_explicit
    #title = getattr(obj, 'Title', None)
    title = None
    if base_hasattr(obj, 'Title'):
        title = getattr(obj, 'Title', None)
    if safe_callable(title):
        title = title()
    if title:
        return title
    item_id = getattr(obj, 'getId', None)
    if safe_callable(item_id):
        item_id = item_id()
    if item_id and not isIDAutoGenerated(context, item_id):
        return item_id
    if empty_value is _marker:
        empty_value = getEmptyTitle(context)
    return empty_value

def getSiteEncoding(context):
    default = 'utf-8'
    pprop = getToolByName(context, 'portal_properties')
    site_props = getToolByName(pprop, 'site_properties', None)
    if site_props is None:
        return default
    return site_props.getProperty('default_charset', default)

def portal_utf8(context, str, errors='strict'):
    charset = getSiteEncoding(context)
    if charset.lower() in ('utf-8', 'utf8'):
        # Test
        unicode(str, 'utf-8', errors)
        return str
    else:
        return unicode(str, charset, errors).encode('utf-8', errors)

def utf8_portal(context, str, errors='strict'):
    charset = getSiteEncoding(context)
    if charset.lower() in ('utf-8', 'utf8'):
        # Test
        unicode(str, 'utf-8', errors)
        return str
    else:
        return unicode(str, 'utf-8', errors).encode(charset, errors)

def getEmptyTitle(context, translated=True):
    """Returns string to be used for objects with no title or id"""
    # The default is an extra fancy unicode elipsis
    empty = unicode('\x5b\xc2\xb7\xc2\xb7\xc2\xb7\x5d', 'utf-8', 'ignore')
    if translated:
        empty = _(u'title_unset', default=empty)
    return empty

def typesToList(context):
    ntp = getToolByName(context, 'portal_properties').navtree_properties
    ttool = getToolByName(context, 'portal_types')
    bl = ntp.getProperty('metaTypesNotToList', ())
    bl_dict = {}
    for t in bl:
        bl_dict[t] = 1
    all_types = ttool.listContentTypes()
    wl = [t for t in all_types if not bl_dict.has_key(t)]
    return wl

def normalizeString(text, context=None, encoding=None, relaxed=False):
    assert (context is not None) or (encoding is not None), \
           'Either context or encoding must be provided'
    # Make sure we are dealing with a stringish type
    if not isinstance(text, basestring):
        # This most surely ends up in something the user does not expect
        # to see. But at least it does not break.
        text = repr(text)

    # Make sure we are dealing with a unicode string
    if not isinstance(text, unicode):
        if encoding is None:
            encoding = getSiteEncoding(context)
        text = unicode(text, encoding)

    text = text.strip()
    if not relaxed:
        text = text.lower()
    text = normalizeUnicode(text)

    base = text
    ext  = ""

    m = FILENAME_REGEX.match(text)
    if m is not None:
        base = m.groups()[0]
        ext  = m.groups()[1]

    base = IGNORE_REGEX.sub("", base)

    if not relaxed:
        base = NON_WORD_REGEX.sub("-", base)
    else:
        base = DANGEROUS_CHARS_REGEX.sub("-", base)

    base = EXTRA_DASHES_REGEX.sub("", base)

    if ext != "":
        base = base + "." + ext
    return base

class IndexIterator:
    """An iterator used to generate tabindexes. Note that tabindexes are not as
       good for accessibility as once thought, and are largely disabled with
       this iterator.
       
       Only the first iteration of an iterator instantiated with mainSlot=True
       will get an index:

        >>> i = IndexIterator(pos=10, mainSlot=True)
        >>> i.next()
        10

       Subsequent iterations will get None (thus removing the tabindex
       attribute):

        >>> i.next() is None
        True

       Outside the mainSlot all iterations will get None:

        >>> i = IndexIterator(pos=10, mainSlot=False)
        >>> i.next() is None
        True

        >>> i.next() is None
        True
    """
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, upper=100000, pos=0, mainSlot=True):
        self.upper=upper
        self.pos=pos
        self.mainSlot=mainSlot

        if not mainSlot:
            self.disabled = True
        else:
            self.disabled = False

    def next(self):
        if self.disabled:
            return None
        self.disabled = True
        return self.pos

class ToolInit(CMFCoreToolInit):

    def getProductContext(self, context):
        name = '_ProductContext__prod'
        return getattr(context, name, getattr(context, '__prod', None))

    def getPack(self, context):
        name = '_ProductContext__pack'
        return getattr(context, name, getattr(context, '__pack__', None))

    def getIcon(self, context, path):
        pack = self.getPack(context)
        icon = None
        # This variable is just used for the log message
        icon_path = path
        try:
            icon = Globals.ImageFile(path, pack.__dict__)
        except (IOError, OSError):
            # Fallback:
            # Assume path is relative to CMFPlone directory
            path = abspath(join(PACKAGE_HOME, path))
            try:
                icon = Globals.ImageFile(path, pack.__dict__)
            except (IOError, OSError):
                # if there is some problem loading the fancy image
                # from the tool then  tell someone about it
                log(('The icon for the product: %s which was set to: %s, '
                     'was not found. Using the default.' %
                     (self.product_name, icon_path)))
        return icon

    def initialize(self, context):
        """ Wrap the CMFCore Tool Init method """
        CMFCoreToolInit.initialize(self, context)
        for tool in self.tools:
            # Get the icon path from the tool
            path = getattr(tool, 'toolicon', None)
            if path is not None:
                pc = self.getProductContext(context)
                if pc is not None:
                    pid = pc.id
                    name = split(path)[1]
                    icon = self.getIcon(context, path)
                    if icon is None:
                        # Icon was not found
                        return
                    icon.__roles__ = None
                    tool.icon = 'misc_/%s/%s' % (self.product_name, name)
                    misc = OFS.misc_.misc_
                    Misc = OFS.misc_.Misc_
                    if not hasattr(misc, pid):
                        setattr(misc, pid, Misc(pid, {}))
                    getattr(misc, pid)[name] = icon


def _createObjectByType(type_name, container, id, *args, **kw):
    """Create an object without performing security checks

    invokeFactory and fti.constructInstance perform some security checks
    before creating the object. Use this function instead if you need to
    skip these checks.

    This method uses some code from
    CMFCore.TypesTool.FactoryTypeInformation.constructInstance
    to create the object without security checks.
    """
    id = str(id)
    typesTool = getToolByName(container, 'portal_types')
    fti = typesTool.getTypeInfo(type_name)
    if not fti:
        raise ValueError, 'Invalid type %s' % type_name

    # we have to do it all manually :(
    p = container.manage_addProduct[fti.product]
    m = getattr(p, fti.factory, None)
    if m is None:
        raise ValueError, ('Product factory for %s was invalid' %
                           fti.getId())

    # construct the object
    m(id, *args, **kw)
    ob = container._getOb( id )

    return fti._finishConstruction(ob)


def safeToInt(value):
    """Convert value to integer or just return 0 if we can't"""
    try:
        return int(value)
    except ValueError:
        return 0

release_levels = ('alpha', 'beta', 'candidate', 'final')
rl_abbr = {'a':'alpha', 'b':'beta', 'rc':'candidate'}

def versionTupleFromString(v_str):
    """Returns version tuple from passed in version string

        >>> versionTupleFromString('1.2.3')
        (1, 2, 3, 'final', 0)

        >>> versionTupleFromString('2.1-final1 (SVN)')
        (2, 1, 0, 'final', 1)

        >>> versionTupleFromString('3-beta')
        (3, 0, 0, 'beta', 0)

        >>> versionTupleFromString('2.0a3')
        (2, 0, 0, 'alpha', 3)

        >>> versionTupleFromString('foo') is None
        True
        """
    regex_str = "(^\d+)[.]?(\d*)[.]?(\d*)[- ]?(alpha|beta|candidate|final|a|b|rc)?(\d*)"
    v_regex = re.compile(regex_str)
    match = v_regex.match(v_str)
    if match is None:
        v_tpl = None
    else:
        groups = list(match.groups())
        for i in (0, 1, 2, 4):
            groups[i] = safeToInt(groups[i])
        if groups[3] is None:
            groups[3] = 'final'
        elif groups[3] in rl_abbr.keys():
            groups[3] = rl_abbr[groups[3]]
        v_tpl = tuple(groups)
    return v_tpl

def getFSVersionTuple():
    """Reads version.txt and returns version tuple"""
    vfile = "%s/version.txt" % PACKAGE_HOME
    v_str = open(vfile, 'r').read().lower()
    return versionTupleFromString(v_str)


def transaction_note(note):
    """Write human legible note"""
    T=transaction.get()
    if isinstance(note, unicode):
        # Convert unicode to a regular string for the backend write IO.
        # UTF-8 is the only reasonable choice, as using unicode means
        # that Latin-1 is probably not enough.
        note = note.encode('utf-8', 'replace')

    if (len(T.description)+len(note))>=65535:
        log('Transaction note too large omitting %s' % str(note))
    else:
        T.note(str(note))


def base_hasattr(obj, name):
    """Like safe_hasattr, but also disables acquisition."""
    return safe_hasattr(aq_base(obj), name)


def safe_hasattr(obj, name, _marker=object()):
    """Make sure we don't mask exceptions like hasattr().

    We don't want exceptions other than AttributeError to be masked,
    since that too often masks other programming errors.
    Three-argument getattr() doesn't mask those, so we use that to
    implement our own hasattr() replacement.
    """
    return getattr(obj, name, _marker) is not _marker


def safe_callable(obj):
    """Make sure our callable checks are ConflictError safe."""
    if safe_hasattr(obj, '__class__'):
        if safe_hasattr(obj, '__call__'):
            return True
        else:
            return isinstance(obj, ClassType)
    else:
        return callable(obj)


def safe_unicode(value, encoding='utf-8'):
    """Converts a value to unicode, even it is already a unicode string.

        >>> from Products.CMFPlone.utils import safe_unicode

        >>> safe_unicode('spam')
        u'spam'
        >>> safe_unicode(u'spam')
        u'spam'
        >>> safe_unicode(u'spam'.encode('utf-8'))
        u'spam'
        >>> safe_unicode('\xc6\xb5')
        u'\u01b5'
        >>> safe_unicode(u'\xc6\xb5'.encode('iso-8859-1'))
        u'\u01b5'
        >>> safe_unicode('\xc6\xb5', encoding='ascii')
        u'\u01b5'
        >>> safe_unicode(1)
        1
        >>> print safe_unicode(None)
        None
    """
    if isinstance(value, unicode):
        return value
    elif isinstance(value, basestring):
        try:
            value = unicode(value, encoding)
        except (UnicodeDecodeError):
            value = value.decode('utf-8', 'replace')
    return value


def tuplize(value):
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)

def _detuplize(interfaces, append):
    if isinstance(interfaces, (tuple, list)):
        for sub in interfaces:
            _detuplize(sub, append)
    else:
        append(interfaces)

def flatten(interfaces):
    flattened = []
    _detuplize(interfaces, flattened.append)
    return tuple(flattened)

def directlyProvides(obj, *interfaces):
    # convert any Zope 2 interfaces to Zope 3 using fromZ2Interface
    interfaces = flatten(interfaces)
    normalized_interfaces = []
    for i in interfaces:
        try:
            i = fromZ2Interface(i)
        except ValueError: # already a Zope 3 interface
            pass
        assert issubclass(i, zope.interface.Interface)
        normalized_interfaces.append(i)
    return zope.interface.directlyProvides(obj, *normalized_interfaces)

def classImplements(class_, *interfaces):
    # convert any Zope 2 interfaces to Zope 3 using fromZ2Interface
    interfaces = flatten(interfaces)
    normalized_interfaces = []
    for i in interfaces:
        try:
            i = fromZ2Interface(i)
        except ValueError: # already a Zope 3 interface
            pass
        assert issubclass(i, zope.interface.Interface)
        normalized_interfaces.append(i)
    return zope.interface.classImplements(class_, *normalized_interfaces)

def classDoesNotImplement(class_, *interfaces):
    # convert any Zope 2 interfaces to Zope 3 using fromZ2Interface
    interfaces = flatten(interfaces)
    normalized_interfaces = []
    for i in interfaces:
        try:
            i = fromZ2Interface(i)
        except ValueError: # already a Zope 3 interface
            pass
        assert issubclass(i, zope.interface.Interface)
        normalized_interfaces.append(i)
    implemented = implementedBy(class_)
    for iface in normalized_interfaces:
        implemented = implemented - iface
    return zope.interface.classImplementsOnly(class_, implemented)

def webdav_enabled(obj, container):
    """WebDAV check used in externalEditorEnabled.py"""

    # Object implements lock interface
    interface_tool = getToolByName(container, 'portal_interface')
    if not interface_tool.objectImplements(obj, 'webdav.WriteLockInterface.WriteLockInterface'):
        return False

    # Backwards compatibility code for AT < 1.3.6
    if safe_hasattr(obj, '__dav_marshall__'):
        if obj.__dav_marshall__ == False:
            return False
    return True


# Copied 'unrestricted_rename' from ATCT migrations to avoid
# a dependency.

from App.Dialogs import MessageDialog
from OFS.CopySupport import CopyError
from OFS.CopySupport import eNotSupported
from cgi import escape
import sys

def _unrestricted_rename(container, id, new_id):
    """Rename a particular sub-object

    Copied from OFS.CopySupport

    Less strict version of manage_renameObject:
        * no write lock check
        * no verify object check from PortalFolder so it's allowed to rename
          even unallowed portal types inside a folder
    """
    try:
        container._checkId(new_id)
    except:
        raise CopyError, MessageDialog(
              title='Invalid Id',
              message=sys.exc_info()[1],
              action ='manage_main')
    ob=container._getOb(id)
    if not ob.cb_isMoveable():
        raise CopyError, eNotSupported % escape(id)
    try:
        ob._notifyOfCopyTo(container, op=1)
    except:
        raise CopyError, MessageDialog(
              title='Rename Error',
              message=sys.exc_info()[1],
              action ='manage_main')
    container._delObject(id)
    ob = aq_base(ob)
    ob._setId(new_id)

    # Note - because a rename always keeps the same context, we
    # can just leave the ownership info unchanged.
    container._setObject(new_id, ob, set_owner=0)
    ob = container._getOb(new_id)
    ob._postCopy(container, op=1)

    return None


# Copied '_getSecurity' from Archetypes.utils to avoid a dependency.

from AccessControl import ClassSecurityInfo

def _getSecurity(klass, create=True):
    # a Zope 2 class can contain some attribute that is an instance
    # of ClassSecurityInfo. Zope 2 scans through things looking for
    # an attribute that has the name __security_info__ first
    info = vars(klass)
    security = None
    for k, v in info.items():
        if hasattr(v, '__security_info__'):
            security = v
            break
    # Didn't found a ClassSecurityInfo object
    if security is None:
        if not create:
            return None
        # we stuff the name ourselves as __security__, not security, as this
        # could theoretically lead to name clashes, and doesn't matter for
        # zope 2 anyway.
        security = ClassSecurityInfo()
        setattr(klass, '__security__', security)
    return security

def scale_image(image_file, max_size=None, default_format=None):
    """Scales an image down to at most max_size preserving aspect ratio
    from an input file

        >>> import Products.CMFPlone
        >>> import os
        >>> from StringIO import StringIO
        >>> from Products.CMFPlone.utils import scale_image
        >>> from PIL import Image

    Let's make a couple test images and see how it works (all are
    100x100), the gif is palletted mode::

        >>> plone_path = os.path.dirname(Products.CMFPlone.__file__)
        >>> pjoin = os.path.join
        >>> path = pjoin(plone_path, 'tests', 'images')
        >>> orig_jpg = open(pjoin(path, 'test.jpg'))
        >>> orig_png = open(pjoin(path, 'test.png'))
        >>> orig_gif = open(pjoin(path, 'test.gif'))

    We'll also make some evil non-images, including one which
    masquerades as a jpeg (which would trick OFS.Image)::

        >>> invalid = StringIO('<div>Evil!!!</div>')
        >>> sneaky = StringIO('\377\330<div>Evil!!!</div>')

    OK, let's get to it, first check that our bad images fail:

        >>> scale_image(invalid, (50, 50))
        Traceback (most recent call last):
        ...
        IOError: cannot identify image file
        >>> scale_image(sneaky, (50, 50))
        Traceback (most recent call last):
        ...
        IOError: cannot identify image file

    Now that that's out of the way we check on our real images to make
    sure the format and mode are preserved, that they are scaled, and that they
    return the correct mimetype::

        >>> new_jpg, mimetype = scale_image(orig_jpg, (50, 50))
        >>> img = Image.open(new_jpg)
        >>> img.size
        (50, 50)
        >>> img.format
        'JPEG'
        >>> mimetype
        'image/jpeg'

        >>> new_png, mimetype = scale_image(orig_png, (50, 50))
        >>> img = Image.open(new_png)
        >>> img.size
        (50, 50)
        >>> img.format
        'PNG'
        >>> mimetype
        'image/png'

        >>> new_gif, mimetype = scale_image(orig_gif, (50, 50))
        >>> img = Image.open(new_gif)
        >>> img.size
        (50, 50)
        >>> img.format
        'GIF'
        >>> img.mode
        'P'
        >>> mimetype
        'image/gif'

    We should also preserve the aspect ratio by scaling to the given
    width only unless told not to (we need to reset out files before
    trying again though::

        >>> orig_jpg.seek(0)
        >>> new_jpg, mimetype = scale_image(orig_jpg, (70, 100))
        >>> img = Image.open(new_jpg)
        >>> img.size
        (70, 70)

        >>> orig_jpg.seek(0)
        >>> new_jpg, mimetype = scale_image(orig_jpg, (70, 50))
        >>> img = Image.open(new_jpg)
        >>> img.size
        (50, 50)

    """
    if max_size is None:
        max_size = IMAGE_SCALE_PARAMS['scale']
    if default_format is None:
        default_format = IMAGE_SCALE_PARAMS['default_format']
    # Make sure we have ints
    size = (int(max_size[0]), int(max_size[1]))
    # Load up the image, don't try to catch errors, we want to fail miserably
    # on invalid images
    image = Image.open(image_file)
    # When might image.format not be true?
    format = image.format
    mimetype = 'image/%s'%format.lower()
    cur_size = image.size
    # from Archetypes ImageField
    # consider image mode when scaling
    # source images can be mode '1','L,','P','RGB(A)'
    # convert to greyscale or RGBA before scaling
    # preserve palletted mode (but not pallette)
    # for palletted-only image formats, e.g. GIF
    # PNG compression is OK for RGBA thumbnails
    original_mode = image.mode
    if original_mode == '1':
        image = image.convert('L')
    elif original_mode == 'P':
        image = image.convert('RGBA')
    # Rescale in place with an method that will not alter the aspect ratio
    # and will only shrink the image not enlarge it.
    image.thumbnail(size, resample=IMAGE_SCALE_PARAMS['algorithm'])
    # preserve palletted mode for GIF and PNG
    if original_mode == 'P' and format in ('GIF', 'PNG'):
        image = image.convert('P')
    # Save
    new_file = StringIO()
    image.save(new_file, format, quality=IMAGE_SCALE_PARAMS['quality'])
    new_file.seek(0)
    # Return the file data and the new mimetype
    return new_file, mimetype


# Keep these here to not fully change the old API
# Put these at the end to avoid an ImportError for safe_unicode
from i18nl10n import utranslate
from i18nl10n import ulocalized_time
from i18nl10n import getGlobalTranslationService

