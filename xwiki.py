from xml.etree.ElementTree import Element, SubElement, dump, tostring, ElementTree
from os import path

class XWikiFile(object):

    def __init__(self):
        self.title = ""
        self.qualifier = None
        self.content = ""
        self.parent_node = None
        self.author = "XWiki.OAMigrator"
        self.last_update = "1500000000000"
        self.created_at = "1500000000000"
        self.path_prefix = "Archiv OpenAtrium"

    # returns the xml file descriptor with its identifier but without any content
    def build_path(self):
        if self.parent_node is None:
            return self.qualifier

        return self.parent_node.build_path() + "." + self.qualifier

    def build_prefixed_path(self):
        return self.path_prefix + "." + self.build_path()

    def build_relative_path(self, origin):
        return path.relpath(self.build.prefixed_path().replace('.', path.sep), origin.replace('.', path.sep)).replace(path.sep, '.')

    def build_xml_content_file(self):
        root = Element("xwikidoc")
        root.attrib["version"] = "1.3"
        root.attrib["reference"] = self.build_prefixed_path() + ".WebHome"
        root.attrib["locale"] = ""
        SubElement(root, "web").text = self.build_prefixed_path()
        SubElement(root, "name").text = "WebHome"
        SubElement(root, "language")
        SubElement(root, "defaultLanguage").text = "de"
        SubElement(root, "translation").text = "0"
        SubElement(root, "creator").text = "XWiki.OAMigrator"
        SubElement(root, "creationDate").text = ""
        SubElement(root, "parent").text = (self.parent_node.build_prefixed_path() if self.parent_node else self.path_prefix) + ".WebHome"
        SubElement(root, "author").text = self.get_xwiki_author()
        SubElement(root, "contentAuthor").text = self.get_xwiki_author()
        SubElement(root, "date").text = ""
        SubElement(root, "contentUpdateDate").text = ""
        SubElement(root, "version").text = "1"
        SubElement(root, "title").text = self.title
        SubElement(root, "comment").text = "Migration OpenAtrium"
        SubElement(root, "minorEdit").text = "false"
        SubElement(root, "syntaxId").text = "markdown/1.2"
        #SubElement(root, "syntaxId").text = "mediawiki/1.6"
        SubElement(root, "hidden").text = "false"
        SubElement(root, "content").text = self.content

        return tostring(root)

    def get_xwiki_author(self):
        return "XWiki." + self.author

class XWikiPage(XWikiFile):

    def __init__(self):
        self.is_page = True
        super(XWikiPage, self).__init__()

class XWikiAttachement(XWikiFile):

    def __init__(self):
        self.is_page = False
        super(XWikiPage, self).__init__()

