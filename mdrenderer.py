# coding: utf-8

"""
    Markdown renderer
    ~~~~~~~~~~~~~~~~~

    This class renders parsed markdown back to markdown.
    It is useful for automatic modifications of the md contents.

    :copyright: (c) 2015 by Jaroslav Kysela
    :licence: WTFPL 2
"""

from mistune import Renderer
import re

class MdRenderer(Renderer):

  def init(self, current_page, pages):
    self.current_page = current_page
    self.pages = pages
    self.is_atrium_link = re.compile(r'https?://atrium\.studieren-ohne-grenzen\.org/[\S]+?/node/([\d]+)[\S]*?|https?://studieren-ohne-grenzen\.org/atrium/[\S]+?/node/([\d]+)[\S]*?|https?://www\.studieren-ohne-grenzen\.org/[\S]+?/node/([\d]+)[\S]*?')

  def get_block(text):
    type = text[0]
    p = text.find(':')
    if p <= 0:
      return ('', '', '')
    l = int(text[1:p])
    t = text[p+1:p+1+l]
    return (text[p+1+l:], type, t)

  def newline(self):
    return '\n'

  def text(self, text):
    return text

  def linebreak(self):
    return '\n'

  def hrule(self):
    return '---\n'

  def header(self, text, level, raw=None):
    return '#'*(level+1) + ' ' + text + '\n\n'

  def paragraph(self, text):
    return text + '\n\n'

  def list(self, text, ordered=True):
    r = ''
    while text:
      text, type, t = MdRenderer.get_block(text)
      if type == 'l':
        r += (ordered and ('# ' + t) or ('* ' + t)) + '\n'
    return r

  def list_item(self, text):
    return 'l' + str(len(text)) + ':' + text

  def block_code(self, code, lang=None):
    return '```\n' + code + '\n```\n'

  def block_quote(self, text):
    r = ''
    for line in text.splitlines():
      r += (line and '> ' or '') + line + '\n'
    return r

  def _emphasis(self, text, pref):
    return pref + text + pref + ' '

  def emphasis(self, text):
    return self._emphasis(text, '_')

  def double_emphasis(self, text):
    return self._emphasis(text, '__')

  def strikethrough(self, text):
    return self._emphasis(text, '~~')

  def codespan(self, text):
    return '`' + text + '`'

  def get_atrium_page(self, link):
    m = self.is_atrium_link.match(link)
    if m:
      linked_node = None
      if m.group(1) is not None:
        linked_node = int(m.group(1))
      elif m.group(2) is not None:
        linked_node = int(m.group(2))

      if linked_node in self.pages:
        linked_page = self.pages[linked_node][0]
        return linked_page
    return False

  def autolink(self, link, is_email=False):
    linked_page = self.get_atrium_page(link) 
    if linked_page != False:
        new_link = self.wiki_link('doc:'+linked_page.build_prefixed_path()+'.WebHome', linked_page.title)
        new_link = new_link.replace("\.", "\\.") # the xwiki markdown processor "unescapes" the links. Hence, we need to escape the escape.
        new_link = new_link.replace("\:", "\\:") # the xwiki markdown processor "unescapes" the links. Hence, we need to escape the escape.
        # replace text and link in the pages itself... it is quite a dirty hack
        self.current_page.content = self.current_page.content.replace('('+link+')', new_link)
        self.current_page.content = self.current_page.content.replace('[' + link + ']', '')
        return new_link
    return '<' + link + '>'

  def link(self, link, title, text, image=False):
    linked_page = self.get_atrium_page(link)
    if not image and linked_page != False:
        new_link = self.wiki_link('doc:'+linked_page.build_prefixed_path()+'.WebHome', text)
        new_link = new_link.replace("\.", "\\.") # the xwiki markdown processor "unescapes" the links. Hence, we need to escape the escape.
        new_link = new_link.replace("\:", "\\:") # the xwiki markdown processor "unescapes" the links. Hence, we need to escape the escape.
        # replace text and link in the pages itself... it is quite a dirty hack
        self.current_page.content = self.current_page.content.replace('('+link+')', new_link)
        self.current_page.content = self.current_page.content.replace('[' + text + ']', '')

        return new_link

    r = (image and '!' or '') + '[' + text + '](' + link + ')'
    if title:
      r += '"' + title + '"'
    return r

  def wiki_link(self, link, text):
    return '[[%s|%s]]' % (text, link)

  def image(self, src, title, text):
    self.link(src, title, text, image=True)

  def table(self, header, body):
    hrows = []
    while header:
      header, type, t = MdRenderer.get_block(header)
      if type == 'r':
        flags = {}
        cols = []
        while t:
          t, type2, t2 = MdRenderer.get_block(t)
          if type2 == 'f':
            fl, v = t2.split('=')
            flags[fl] = v
          elif type2 == 'c':
            cols.append(type('',(object,),{'flags':flags,'text':t2})())
        hrows.append(cols)
    brows = []
    while body:
      body, type, t = MdRenderer.get_block(body)
      if type == 'r':
        flags = {}
        cols = []
        while t:
          t, type2, t2 = MdRenderer.get_block(t)
          if type2 == 'f':
            fl, v = t2.split('=')
            flags[fl] = v
          elif type2 == 'c':
            cols.append(type('',(object,),{'flags':flags,'text':t2})())
        brows.append(cols)
    colscount = 0
    colmax = [0] * 100
    align = [''] * 100
    for row in hrows + brows:
      colscount = max(len(row), colscount)
      i = 0
      for col in row:
        colmax[i] = max(len(col.text), colmax[i])
        if 'align' in col.flags:
          align[i] = col.flags['align'][0]
        i += 1
    r = ''
    for row in hrows:
      i = 0
      for col in row:
        if i > 0:
          r += ' | '
        r += col.text.ljust(colmax[i])
        i += 1
      r += '\n'
    for i in range(colscount):
      if i > 0:
        r += ' | '
      if align[i] == 'c':
        r += ':' + '-'.ljust(colmax[i]-2, '-') + ':'
      elif align[i] == 'l':
        r += ':' + '-'.ljust(colmax[i]-1, '-')
      elif align[i] == 'r':
        r +=  '-'.ljust(colmax[i]-1, '-') + ':'
      else:
        r += '-'.ljust(colmax[i], '-')
    r += '\n'
    for row in brows:
      i = 0
      for col in row:
        if i > 0:
          r += ' | '
        r += col.text.ljust(colmax[i])
        i += 1
      r += '\n'
    return r

  def table_row(self, content):
    return 'r' + str(len(content)) + ':' + content

  def table_cell(self, content, **flags):
    content = content.replace('\n', ' ')
    r = ''
    for fl in flags:
      v = flags[fl]
      if type(v) == type(True):
        v = v and 1 or 0
      v = str(v) and str(v) or ''
      r += 'f' + str(len(fl) + 1 + len(v)) + ':' + fl + '=' + v
    return r + 'c' + str(len(content)) + ':' + content

  def footnote_ref(self, key, index):
    return '[^' + str(index) + ']'

  def footnote_item(self, key, text):
    r = '[^' + str(index) + ']:\n'
    for l in text.split('\n'):
      r += '  ' + l.lstrip().rstrip() + '\n'
    return r

  def footnotes(self, text):
    return text
