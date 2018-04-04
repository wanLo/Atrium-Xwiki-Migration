from xwiki import *
import MySQLdb
from html_converter import FromString
import os
import unicodedata
import re

db = MySQLdb.connect(host = "localhost", user = "root" , passwd = "a1b2c3", db = "atrium")
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
            order by n.nid desc, r.vid desc limit 400 offset 4000") # for testing

    migrated = []
    # since the syntax for xwiki documents with history is not particularly beautiful, we skip
    # history migration. However, we keep atrium, hence is is not that bad.
    db_elems = cursor.fetchall()

    productive_page_by_nid = {}
    for elem in db_elems:
        if elem[0] not in productive_page_by_nid:
            migrated_elem = convert_single_entry(elem)
            migrated.append(migrated_elem)
            productive_page_by_nid[elem[0]] = migrated_elem

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


    create_project_file(migrated)
    create_page_files(migrated)
    # TODO clean up references in links

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

def find_parent(page):
    menu_information = menu_link_information[page.nid]
    book_root = menu_information[1]
    node_parent_mlid = menu_information[2]
    predecessor_mlid = node_parent_mlid
    if book_root == menu_information[0]: # we are root!
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
    ascii_title = ascii_title.replace("/", "_")
    # if title has any . we convert it to / which is bad again
    ascii_title = ascii_title.replace(".", "-")
    # only if we actually get problems with xwiki import
    ascii_title = ''.join([c for c in ascii_title if ord(c) < 128])

    # bad characters (to be safe)
    ascii_title = ascii_title.replace("<", "")
    ascii_title = ascii_title.replace(">", "")
    ascii_title = ascii_title.replace("&", "&amp;")

    return ascii_title

def convert_single_entry(atrium_entry):
    page = XWikiPage()
    page.nid = atrium_entry[0]
    page.vid = atrium_entry[1]
    page.content = process_page_content(atrium_entry[2])
    page.title = atrium_entry[3]
    page.qualifier = normalize_title(page.title)

    # TODO create a list of links to iterate over for attachements, however, serialize the list and
    # migrate attachements separately
    # we need (page -> []links)

    print("Converted page with nid %d and vid %d" % (page.nid, page.vid))

    return page

def process_page_content(body):
    converted_text = FromString(body)

    return converted_text

def create_project_file(pages):
    project = "<package>\n"
    project += create_header()
    project += '\n'
    project += "<files>\n"
    for page in pages:
        # try to merge by default
        project += "<file language=\"de\" defaultAction=\"0\">"
        project += page.build_prefixed_path() + ".WebHome"
        project += "</file>\n"
    project += "</files>\n"
    project += "</package>"

    f = open(output_folder_path + "/package.xml", "w")
    f.write(project)
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

    initialize()
    convert_atrium_db_to_xar()
