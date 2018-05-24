from xwiki import *
from wikilink_lexer import WikiLinkInlineLexer
from mdrenderer import MdRenderer
import MySQLdb
import os
import unicodedata
import re
import pypandoc
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from joblib import Parallel, delayed
import multiprocessing
import mistune

db = MySQLdb.connect(host = "localhost", user = "root" , passwd = "", db = "atrium")
output_folder_path = "result"
parent_cursor = db.cursor()

pages_by_node_id = {}
menu_link_information = {}
mlid_to_nid = {}

def convert_atrium_db_to_xar():
    print("converting to xar archive...")
    print("Writing result to output folder >%s<" % output_folder_path)

    cursor = db.cursor()
    cursor.execute("select r.nid, r.vid, r.body, n.title \
            from openatrium_node as n \
            inner join openatrium_node_revisions as r \
            on n.nid = r.nid \
            where n.type = \"book\" \
            order by n.nid desc, r.vid desc")

    migrated = []
    # since the syntax for xwiki documents with history is not particularly beautiful, we skip
    # history migration. However, we keep atrium, hence is is not that bad.
    db_elems = cursor.fetchall()

    productive_page_by_nid = {}
    to_migrate = []
    for elem in db_elems:
        if elem[0] not in productive_page_by_nid:
            to_migrate.append(elem)
            productive_page_by_nid[elem[0]] = elem

    num_cores = multiprocessing.cpu_count()
    migrated = Parallel(n_jobs=num_cores)(delayed(convert_single_entry)(elem) for elem in to_migrate)

    # we could refactor this away! However, leave it since time is short and this will only run once
    for item in migrated:
        if item.nid not in pages_by_node_id:
            pages_by_node_id[item.nid] = []

        pages_by_node_id[item.nid].append(item)

    # however, use it to assert the invariant that we only have one page version
    for nid, pages_list in pages_by_node_id.items():
        assert(len(pages_list) == 1)

    assert(menu_link_information != {})
    assert(pages_by_node_id != {})
    assert(mlid_to_nid != {})
    for index, pages_of_nid in pages_by_node_id.items():
        print("trying to find parents of page %s" % index)
        for page in pages_of_nid:
            if page.nid in menu_link_information:
                # we may have multiple versions!
                parent_nid = find_parent(page)
                if parent_nid != None:
                    if parent_nid not in pages_by_node_id:
                        # add to root page
                        print("WARN: There is no page with nid %d of page nid=%d"
                                % (parent_nid, page.nid))
                        continue

                    parent_set = pages_by_node_id[parent_nid]
                    page.parent_node = parent_set[0] # take first. nid does not change
                    assert(page.parent_node is not None)

            else:
                print("Page with nid %s has no link information" % page.nid)

    prepend_groups(migrated)

    all_xwiki_pages = migrated + [page for nid, page in groups.items()]

    adjust_content_links(all_xwiki_pages)

    create_project_file(all_xwiki_pages)
    create_page_files(all_xwiki_pages)

def prepend_groups(migrated):
    for page in migrated:
        if page.parent_node is not None:
            continue

        if page.nid not in page_to_group:
            print("WARN: Could not find Group node for node id %d" % page.nid)
            page.parent_node = groups[-1]
            continue

        group_nid = page_to_group[page.nid]
        if group_nid in groups:
            group = groups[group_nid]
            page.parent_node = group
        else:
            page.parent_node = groups[-1]
            print("WARN: Could not find Group node for group_nid %d" % group_nid)

def initialize():
    parent_cursor.execute("select b.nid, ml.mlid, b.bid, ml.plid \
      from openatrium_menu_links as ml \
      inner join openatrium_book as b \
      on b.mlid = ml.mlid")
    elems = parent_cursor.fetchall()
    global mlid_to_nid
    global menu_link_information
    mlid_to_nid = dict(zip((l[1] for l in elems), (l[0] for l in elems)))
    menu_link_information = dict(zip((l[0] for l in elems), (l[1:] for l in elems)))

    # match book pages to groups
    global page_to_group
    parent_cursor.execute("select n.nid, ac.group_nid from openatrium_og_ancestry as ac \
            inner join openatrium_node as n \
            on ac.nid = n.nid \
            order by n.nid, ac.group_nid")
    elems = parent_cursor.fetchall()
    page_to_group = dict(zip((l[0] for l in elems), (l[1] for l in elems)))

    global titles_by_group
    parent_cursor.execute("select nid, title from openatrium_node where type = \"group\" ")
    elems = parent_cursor.fetchall()
    titles_by_group = dict(zip((l[0] for l in elems), (l[1] for l in elems)))

    global groups
    groups = {}
    for index, title in titles_by_group.items():
        groups[index] = create_group_page(index, title)

    groups[-1] = create_group_page(-1, "Unmatched")

def create_group_page(nid, title):
    page = XWikiPage()
    page.nid = nid
    page.vid = 1

    page.content = title

    page.title = title
    page.qualifier = normalize_title(page.title)

    print("Created group page with nid %d and title %s" % (page.nid, page.title))

    return page

def find_parent(page):
    menu_information = menu_link_information[page.nid]
    book_root = menu_information[1]
    node_parent_mlid = menu_information[2]
    predecessor_mlid = node_parent_mlid
    if book_root == menu_information[0]: # we are at book root.
        return None

    assert(predecessor_mlid != menu_information[0])

    if predecessor_mlid not in mlid_to_nid:
        print("WARN: there is no node id to mlid %d. Tried to find parent for [nid=%d,mlid=%d]" %
                (predecessor_mlid, page.nid, menu_information[0]))
        return None

    return mlid_to_nid[predecessor_mlid]

def normalize_title(title):
    ascii_title = unicodedata.normalize('NFKD', title)
    # if title has any / we would create a directory, must not happen
    ascii_title = ascii_title.replace("/", "\/")
    # if title has any . we convert it to / which is bad again
    ascii_title = ascii_title.replace(".", "\.")
    # only if we actually get problems with xwiki import
    ascii_title = ''.join([c for c in ascii_title if ord(c) < 128])

    ascii_title = ascii_title.replace(":", "\:")

    return ascii_title

def convert_single_entry(atrium_entry):
    page = XWikiPage()
    page.nid = atrium_entry[0]
    page.vid = atrium_entry[1]

    try:
        # pandoc might decide that the page is malformed in weird way.
        page.content = process_page_content(atrium_entry[2])
    except Exception as e:
        page.content = "ERROR during conversion: " + str(e)
        page.content += "nid = %s, vid = %s - contact it!" % (page.nid, page.vid)
        print("Got error: %s, nid = %s, vid = %s" % (str(e), page.nid, page.vid))

    page.title = atrium_entry[3]
    page.qualifier = normalize_title(page.title)

    # TODO create a list of links to iterate over for attachements, however, serialize the list and
    # migrate attachements separately
    # we need (page -> []links)

    print("Converted page with nid %d and vid %d" % (page.nid, page.vid))

    return page

def process_page_content(body):
    converted_text = pypandoc.convert_text(source=body, to="commonmark", format="html", extra_args=("+RTS","-K64m", "-RTS"))

    return converted_text

def adjust_content_links(pages):
    renderer = MdRenderer(pages_by_node_id)
    transform_links = mistune.Markdown(renderer=renderer, inline=WikiLinkInlineLexer(renderer))
    for page in pages:
            page.content = transform_links(page.content)

def create_project_file(pages):
    root = Element("package")
    SubElement(root, "name").text = "SOG Atrium Backup"
    SubElement(root, "description").text = "Migrated Atrium Data importable to XWiki"
    SubElement(root, "license").text = "Not applicable"
    SubElement(root, "author").text = "AtriumMigrator"
    files = SubElement(root, "files")

    for page in pages:
        file_xml = SubElement(files, "file")
        file_xml.attrib["language"] = "de"
        file_xml.attrib["defaultAction"] = "0"
        file_xml.text = page.build_prefixed_path() + ".WebHome"

    f = open(output_folder_path + "/package.xml", "w")
    f.write(tostring(root).decode("utf-8"))
    f.close()

def create_header():
    header = "<name>SOG Atrium Backup</name>\n"
    header += "<description>Migrated Atrium Data importable to XWiki</description>\n"
    header += "<licence>Not public</licence>\n"
    header += "<author>XWiki.Atrium</author>\n"

    return header

def create_page_files(pages):
    for page in pages:
        # check for folders on path
        formal_path = page.build_prefixed_path().replace(".", "/")
        physical_path = output_folder_path + "/" + formal_path
        print("Creating XWiki Page %s" % formal_path)
        if not os.path.exists(physical_path):
            os.makedirs(physical_path)

        xml_tree_string = page.build_xml_content_file()
        f = open(physical_path + "/WebHome.xml", "w")
        f.write(xml_tree_string.decode('utf-8'))
        f.close()

if __name__ == "__main__":
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    print(pypandoc.get_pandoc_formats()[1])
    initialize()
    convert_atrium_db_to_xar()
