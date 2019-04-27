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
            pages.add(json_response['spaces'][i]['links'][1]['href'])
        
        offset+=100

        print(offset)

    return pages

print(get_wiki_pages())