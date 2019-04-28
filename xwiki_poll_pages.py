import requests

user   = ''
passwd = ''

def get_wiki_pages():
    
    offset = 0
    end_reached = False
    pages = set()

    while not end_reached:

        payload = {'media':'json', 'number':'100', 'start':offset}
        pages_response = requests.get('https://wiki.studieren-ohne-grenzen.org/rest/wikis/xwiki/spaces',
                        auth=(user, passwd), params=payload)

        json_response = pages_response.json()

        if (not json_response['spaces']):
            end_reached = True
            continue

        for i in xrange(len(json_response['spaces'])):
            if (json_response['spaces'][i]['links'][1]['href'][:84] !=
                'https://wiki.studieren-ohne-grenzen.org/rest/wikis/xwiki/spaces/Archiv%20OpenAtrium/'):
                pages.add(json_response['spaces'][i]['links'][1]['href'])
        
        offset+=100

        print('found {} of {}'.format(len(pages), offset))

    return pages


def count_md_pages():
    
    md_counter = 0
    page_count = 0
    key_errors = 0
    value_errors = 0

    pages = get_wiki_pages()

    for _ in xrange(len(pages)):

        payload = {'media':'json'}
        url = pages.pop()
        # print(url)
        pages_response = requests.get(url, auth=(user, passwd), params=payload)

        try:
            json_response = pages_response.json()
            if (json_response['syntax']=='markdown/1.2'):
                md_counter+=1
        except KeyError:
            key_errors+=1
        except ValueError:
            value_errors+=1
        
        page_count+=1

        print('markdown: {} / {} ({:.2f}%) | KeyErrors: {} | ValueErrors: {}'.format(
            md_counter, page_count, float(md_counter)/page_count*100, key_errors, value_errors))

    return md_counter


def convert_spaces_url(url):

    url = url[64:]

    i = 0

    while i < len(url):
        if (url[i]=='/'):
            if (url[i:i+8]=='/spaces/'): i+=8
            elif (url[i:i+7]=='/pages/'): i+=7
            else:
                url_before = url[:i-1]
                url_after  = url[i+1:]
                url = url_before + '%2F' + url_after
                i+=3
        else: i+=1

    return 'https://wiki.studieren-ohne-grenzen.org/rest/wikis/xwiki/spaces/' + url

print(count_md_pages())