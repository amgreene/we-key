import cgi
import codecs
import collections
import datetime
import json
import re
import os

from conf import conf
from util import *


at_path_re = r'@([-A-Za-z0-9_]+)'


def uncamel_case(s):
    s = re.sub('([a-z])([A-Z])', r'\1 \2', s)
    s = re.sub('([0-9])([a-zA-Z])', r'\1 \2', s)
    s = re.sub('([a-zA-Z])([0-9])', r'\1 \2', s)
    s = re.sub('-', ' ', s)
    s = re.sub('_', ' ', s)
    return s


def pretty_html(s):
    s = s.replace('&', '&amp;')
    s = s.replace(" '", ' &lsquo;')
    s = s.replace("'", '&rsquo;')
    s = s.replace(' "', ' &ldquo;')
    s = s.replace('"', '&rdquo;')
    # to do: quotes that are not adjacent to a space....
    s = s.replace("--", '&ndash;')
    s = re.sub(r"\\i{(.*?)}", r"<i>\1</i>", s)

    # expand img tags (this is really no longer pretty_html but
    # it's "convert We-Key markup to HTML")
    def img_replacement(m):
        key = m.group('key')
        caption = m.group('caption')
        alignment = (m.group('alignment') or 'left').lower()

        if alignment.startswith('l'):
            alignment_class='pull-left'
        elif alignment.startswith('r'):
            alignment_class='pull-right'
        else:
            alignment_class='center-block'

        i = '<div class="clearfix"></div>'
        i += '<div class="img_holder ' + alignment_class + '">'       # to do: use template
        i += '<a href="/img/' + key + '">'    # to do: use template
        i += '<img style="max-width: 300px"'  # to do: use css class
        i += ' src="/img/' + key + '">'      # to do: use template
        i += "</a>"
        if caption:
            i += "<div class='img_caption'>"  # to do: use template
            i += caption                      # to do: HTML conversion?
            i += "</div>"                     # close img_caption
        i += "</div>"                         # close img_holder
        return i

    s = re.sub(r'\\img{(?P<key>.*?)}({(?P<caption>.*?)})?({(?P<alignment>.*?)})?', img_replacement, s)
    return s


class Info:
    def __init__(self, value=''):
        self.data = collections.defaultdict(list)
        self.string_value = value

    def __unicode__(self):
        return self.string_value

    def __str__(self):
        return str(unicode(self))

    @staticmethod
    def split_key(key):
        if '/' in key:
            return key.split('/', 1)
        return (key, None)
        
    def add(self, key, value):
        key, subkey = Info.split_key(key)
        if subkey:
            # if all we have is a path, assume we're adding to the most recently added one with that key
            # and make sure that exists!
            if not self.has_key(key):
                self.add(key, '')
            return self.data[key][-1].add(subkey, value)
        else:
            new_info = Info(value=value)
            self.data[key].append(new_info)
            return new_info

    def get_with_metadata(self, key):
        key, subkey = Info.split_key(key)
        if subkey:
            return self.data[key].get(subkey)
        else:
            return self.data[key]

    def get(self, key):
        return [i.string_value for i in self.get_with_metadata(key)]

    def has_key(self, key):
        key, subkey = Info.split_key(key)
        if subkey:
            return self.data.get(key).has_key(subkey)
        else:
            return self.data.has_key(key)


class Page:
    cache = {}

    @staticmethod
    def find(page_name):
        return Page.cache.get(page_name, Page(page_name))

    def __init__(self, page_name):
        self.info = Info()
        self.text = ''
        self.xrefs = []
        self.relations = {}
        self.page_name = page_name
        Page.cache[page_name] = self

        if '.' in page_name:
            return
        if '/' in page_name:
            return
        if '\\' in page_name:
            return
        if ':' in page_name:
            return
        
        file_name = page_name + '.wk'
        if file_name[0] == '@':
            file_name = file_name[1:]
        self.load(file_name)
        
        with codecs.open(os.path.join(conf['data_dir'], 'xrefs.json'), 'r', 'utf-8') as x_file:
            self.xrefs = json.load(x_file).get(page_name, [])
        with codecs.open(os.path.join(conf['data_dir'], 'relationships.json'), 'r', 'utf-8') as x_file:
            self.relations = json.load(x_file).get('@' + page_name, {})

    def __unicode__(self):
        return self.page_name

    def __str__(self):
        return str(unicode(self))

    def has_key(self, key):
        return self.info.has_key(key)

    def get(self, key):
        return self.info.get(key)

    def find_name_for(self, at_path):
        try:
            at_path2 = at_path
            if at_path2[0] == '@':
                at_path2 = at_path2[1:]
            at_page = Page.find(at_path2)
            return at_page.name()
        except Exception as e:
            # print e
            for line in data_open('etc.wk'):
                if line.startswith(at_path + ' '):
                    return line.split(' ', 1)[1]
            return uncamel_case(at_path)

    def name(self):
        if self.has_key('name'):
            return self.get('name')[0]
        for line in data_open('etc.wk'):
            if line.startswith('@' + self.page_name + ' '):
                return line.split(' ', 1)[1]
        return uncamel_case(self.page_name)
        
    def find_extended_name_for(self, at_path):
        try:
            at_page = Page.find(at_path)
            n = at_page.name[0]
            parents = []
            parents += at_page.get('father')
            parents += at_page.get('mother')
            if len(parents):
                n += " (Child of " + ", ".join([
                    self.find_name_for(p) for p in parents
                    ]) + ")"
            return n
        except:
            for line in data_open('etc.wk'):
                if line.startswith('@' + at_path + ' '):
                    return line.split(' ', 1)[1]
            return uncamel_case(at_path)
        
    def load(self, file_name):
        if not os.path.exists(os.path.join(conf['data_dir'], file_name)):
            # No file backs up this at_path
            # So just take the atpath itself, and insert spaces where there's camel-casing
            self.info.add('name', uncamel_case(file_name.split('.')[0]))
            # no file means no mtime
            self.mtime = ''
            return
        self.mtime = datetime.datetime.fromtimestamp(
            os.path.getmtime(os.path.join(conf['data_dir'], file_name))).strftime('%Y-%m-%d %H:%M:%S')
        current_infos = []
        parsing_header = True
        for line in data_open(file_name):
            line = line.rstrip()
            if line == '':
                if self.text:
                    self.text += '\n' # blank line (but not at the beginning)
                parsing_header = False
            elif parsing_header and line[0] == '\\':
                if '=' in line:
                    (key, value) = line[1:].split('=', 2)
                else:
                    key=line[1:]
                    value=True
                current_infos = [self.info.add(key, value)]
            elif parsing_header and line.lstrip()[0] == '\\': # indented -- for now, we're not recursing, but we should
                info_indent = len(line.split('\\', 1)[0])
                if info_indent > len(current_infos) + 1:
                    print "Error: indent is too great"
                    print line
                    continue
                current_infos = current_infos[0:info_indent] # handle "popping" up one or more levels
                if '=' in line:
                    (key, value) = line.lstrip()[1:].split('=', 2)
                else:
                    key=line.lstrip()[1:]
                    value=True
                current_infos[-1].add(key, value) # kludge; see above
            else:
                current_infos = [] # anything that isn't an info resets the infos stack
                self.text += line + '\n' # we've eliminated trailing spaces but not the newline

    # TO DO -- if an @Name can be resolved, use the person's real name. Otherwise, expand out the camel case
    def resolve_info(self, key):
        def pretty_print_with_metadata(i):
            s = ''
            try:
                if i == True:
                    pass
                else:
                    s = cgi.escape(unicode(i))  # if i can't be cast to a unicode object for some reason....
            except:
                pass
            if i.has_key('date'):
                s += " on " + cgi.escape(unicode(i.get('date')[0]))
            if i.has_key('place'):
                s += " at " + cgi.escape(unicode(i.get('place')[0]))
            return s

        s = ', '.join([pretty_print_with_metadata(i) for i in self.info.get_with_metadata(key)])
        return self.expand_atpaths(s)


    def expand_atpaths(self, s):
        def do_lookup(at_path):
            at_path = at_path.group(1)
            return "<span class='linkwrapper'><a href='" + at_path + "'>" + self.find_name_for(at_path) + "</a></span>"
        s = re.sub(r'@{(.*?)} ?\\?qua{(.*?)}', r'<span class="linkwrapper"><a href="\1">\2</a></span>', s)
        s = re.sub(at_path_re + r' ?\\?qua{(.*?)}', r'<span class="linkwrapper"><a href="\1">\2</a></span>', s)
        s = re.sub(at_path_re, do_lookup, s) # r'<a href="\1">\1</a>', s)
        return s

    def header_stuff(self, outlines):
        # TO DO - generalize/refactor this (allowing for more complex patterns/hierachies)
        outlines.append("<div class='header'>")
        if self.info.has_key('name'):
            outlines.append("<div class='name'>" + self.resolve_info('name') + "</div>")
        if self.info.has_key('hebname'):
            outlines.append("<div class='hebname'>" + self.resolve_info('hebname') + "</div>")
        if self.info.has_key('born'):
            outlines.append("<div class='born'>Born " + self.resolve_info('born') + "</div>")
        if self.info.has_key('married'):
            outlines.append("<div class='married'>Married " + self.resolve_info('married') + "</div>")
        if self.info.has_key('died'):
            outlines.append("<div class='died'>Died " + self.resolve_info('died') + "</div>")
#        if self.info.has_key('father'):
#            outlines.append("<div class='parent father'>Father: " + self.resolve_info('father') + "</div>")
#        if self.info.has_key('mother'):
#            outlines.append("<div class='parent mother'>Mother: " + self.resolve_info('mother') + "</div>")
        if self.relations.has_key('children'):
            outlines.append("<div class='children'>Children: " + ", ".join([
                self.expand_atpaths(cgi.escape(child_path)) for child_path in self.relations['children']
                ]) + "</div>")
        
        if self.has_key('residence'):
            outlines.append("<div class='residence'>Residence: " + ", ".join([
                self.expand_atpaths(cgi.escape(r)) for r in self.get('residence')
                ]) + "</div>")
        
        if len(self.xrefs):
            outlines.append("<div class='xrefs'>Referenced by: " + ', '.join(
                self.expand_atpaths(cgi.escape(v)) for v in self.xrefs
            ) + "</div>")
        outlines.append("</div>")

    def expand_references(self, line):
        line = re.sub(r'\\addr\{(.*?)\}', r'<span class="addr">\1</a>', line)
        line = re.sub(r'\\age\{(.*?)\}', r'\1', line) # TO DO --> implied birth year
        line = self.expand_atpaths(line)
        line = re.sub(r'(\d{4}-\d{2}-\d{2})', r'<span class="date">\1</span>', line)
        return line

    def format_form(self):
        html = ''
        for line in self.text.split('\n'):
            if ': ' in line:
                html += "<tr><td>" + self.expand_references(re.sub(r': (.*)', r':</td><td><b>\1</b>', line)) + "</td></tr>"
            else:
                if line.strip() == '':
                    line = '&nbsp;' # leave a blank line
                html += "<tr><td colspan=2>" + self.expand_references(line) + "</td></tr>"
        if self.has_key('original'):
            html += "<div class='originals'>"
            for img in self.get('original'):
                if img.startswith('@'):
                    img = img[1:]
                html += "<a href='/img/" + img + "'><img src='/img/" + img + "' /></a>"
                #print img
                #for u in self.get_image_urls(img):
                #    html += "<a href='" + u + "'><img src='" + u + "' /></a>"
            html += "</div>"
        return html

    def format_text(self):
        if self.has_key('isform'):
            return self.format_form()
        paragraphs = self.text.split('\n\n')
        html = ''
        for p in paragraphs:
            p_type = 'p'
            if p.startswith('.heading '):
                p_type = 'h2'
                p = p[9:]
            elif p.startswith('* '):
                p_type = 'ul'
                # replace * with li elements as appropriate
                p = '\n'.join(['<li>' + re.sub(r'^\* ', '', x) + '</li>' for x in p.split('\n')])
            p = pretty_html(p)
            html += "<" + p_type + ">" + self.expand_references(p) + "</" + p_type + ">\n"
        return html

    def find_ancestor_by_path(self, path, x='self'):
        if x is None:
            return None
        if x=='self':
            x = self
        if isinstance(x, unicode):
            x = Page.find(x) # kludge
        if path == '':
            return x
        if path[0] == 'm':
            return self.find_ancestor_by_path(path[1:], (x.get('mother') + [None])[0])
        if path[0] == 'f':
            return self.find_ancestor_by_path(path[1:], (x.get('father') + [None])[0])
        return None

    def generate_ancestors_compact_html(self):
        ff = self.find_ancestor_by_path('ff')
        fm = self.find_ancestor_by_path('fm')
        mf = self.find_ancestor_by_path('mf')
        mm = self.find_ancestor_by_path('mm')
        f = self.find_ancestor_by_path('f')
        m = self.find_ancestor_by_path('m')
        s = []

        def do_grandparent(gp):
            if gp is None:
                return
            s.append("<div class='ftree_grandparent'>" + gp.expand_atpaths(cgi.escape(gp.page_name)))
            if len(gp.get('father')):
                s.append("<div class='greatgrandparents'>" + gp.resolve_info('father') + "</div>")
            if len(gp.get('mother')):
                s.append("<div class='greatgrandparents'>" + gp.resolve_info('mother') + "</div>")
            s.append("</div>")

        s.append("<div class='ftree'>")
        if not ((ff is None) and (fm is None)):
            s.append("<div class='ftree_paternal_grandparents'>")
            do_grandparent(ff)
            do_grandparent(fm)
            s.append("</div>")
        if not ((mf is None) and (mm is None)):
            s.append("<div class='ftree_maternal_grandparents'>")
            do_grandparent(mf)
            do_grandparent(mm)
            s.append("</div>")
        if not ((f is None) and (m is None)):
            s.append("<div class='ftree_parents'>")
            if not (f is None):
                s.append("<div>" + f.expand_atpaths(cgi.escape(f.page_name)) + "</div>")
            if not (m is None):
                s.append("<div>" + m.expand_atpaths(cgi.escape(m.page_name)) + "</div>")
            s.append("</div>")
        s.append("<div class='ftree_central'>" + cgi.escape(self.name()) + "</div>") # no need to self-link
        s.append("</div>")
        return "".join(s)

    def get_image_urls(self, key):
        if key.startswith('@'):
            key = key[1:]
        urls = []
        for line in data_open('images-index.txt'):
            splits = line.strip().split(' ')
            if re.sub('@', '', splits[0]) == key:
                urls += splits[1:]
        return ['/img/' + u for u in urls]

    def turn_page_into_html(self):

        outlines = []
        #outlines.append("<title>" + self.page_name + "</title>")

        self.header_stuff(outlines)
        outlines.append(self.generate_ancestors_compact_html())

        # TwitterBootstrap hierarchy
        outlines.append("<div class='container-fluid'>")
        outlines.append("<div class='row'>")
        outlines.append("<div class='col-xs-12 col-md-8 col-md-offset-2'>")

        outlines.append("<div class='text'>")
        if self.info.has_key('isform'):
            outlines.append("<table cellpadding=0 cellborders=0>")
        is_stub = True
        outlines.append(self.format_text())
        if self.text.strip() != '':
            is_stub = False
        if self.info.has_key('isform'):
            outlines.append("</table>")
        if is_stub:
            outlines.append("This page is a stub. Nothing more is known at this time.")

        outlines.append("<div class='clearfix'></div>") # to make sure floats are closed off

        outlines.append("</div>") # end of text

        if self.mtime:
            outlines.append("<div class='mtime'>Last updated " + self.mtime + "</div>")

        for line in data_open('images-index.txt'):
            splits = line.split(' ')
            if re.sub('@', '', splits[0]) == self.page_name:
                outlines.append("<img class='img_on_page' src='/img/" + self.page_name + "'><br>")
                for url in splits[1:]:
                    outlines.append("<img src='" + url + "'><br>")

        outlines.append("</div>") # end of col
        outlines.append("</div>") # end of row
        outlines.append("</div>") # end of container

        body_block = u'\n'.join([unicode(s) for s in outlines])
        template = open('templates/layout.html', 'r').read()  # for now.... will migrate to Flash/Jinja soon
        template = template.replace('{{ title }}', self.page_name)
        template = template.replace('{{ ga_key }}', conf['ga_key'])
        template = template.replace('{% block body %}{% endblock %}', body_block)


        return template


def make_index():
    refs = collections.defaultdict(set)
    for f in list_wk_files():
        at_path = '@' + ''.join(f.split('.')[:-1])  # drop .wk extention
        for line in data_open(f):
            for m in re.findall(at_path_re, line):
                refs[m].add(at_path)
    
    converted_refs = dict([(k, sorted(list(v))) for (k, v) in refs.items()])
    with codecs.open(os.path.join(conf['data_dir'], 'xrefs.json'), 'w', 'utf-8') as o:
        json.dump(converted_refs, o, ensure_ascii=False, indent=2, sort_keys=True)


def make_relationship_index():
    refs = {}
    def add_value(at_path, relationship, other_at_path):
        if not refs.has_key(at_path):
            refs[at_path] = {}
        if not refs[at_path].has_key(relationship):
            refs[at_path][relationship] = []
        refs[at_path][relationship].append(other_at_path)

    for f in list_wk_files():
        at_path = '@' + ''.join(f.split('.')[:-1])  # drop .wk extention
        p = Page.find(at_path)

        for parent in p.get('father'):
            add_value(at_path, 'father', parent)
            add_value(parent, 'children', at_path)
        for parent in p.get('mother'):
            add_value(at_path, 'mother', parent)
            add_value(parent, 'children', at_path)
        for spouse in p.get('married'):
            add_value(at_path, 'spouses', spouse)
            add_value(spouse, 'spouses', at_path)
    
    with codecs.open(os.path.join(conf['data_dir'], 'relationships.json'), 'w', 'utf-8') as o:
        json.dump(refs, o, ensure_ascii=False, indent=2, sort_keys=True)


def html_index_tags():
    tags = set()
    pages = set()

    for line in data_open('images-index.txt'):
        (key, path) = line.strip().split(' ', 1)
        tags.add(key)

    for f in list_wk_files():
        tags.add(f[:-3])
        pages.add(f[:-3])
        for line in data_open(f):
            for m in re.findall(at_path_re, line):
                tags.add(m)

    outlines = []
    outlines.append("<html><body>")
    for key in sorted(tags):
        if key in pages:
            is_page = 'page'
        else:
            is_page = 'stub'
        outlines.append('<a class="' + is_page + '" href="/' + key + '">'+key+'</a>')
    outlines.append("</body></html>")
    return '<br>'.join(outlines)


def html_index_images():
    outlines = []
    outlines.append("<html><body>")
    for line in data_open('images-index.txt'):
        (key, path) = line.strip().split(' ', 1)
        outlines.append('<a href="/' + key + '">'+key+'</a>')
    outlines.append("</body></html>")
    return '<br>'.join(outlines)


def locate_image(key):
    for line in data_open('images-index.txt'):
        if line.startswith(key + ' '):
            return os.path.join(conf['img_dir'], line.split(' ')[1]).strip()
    return None


if __name__ == '__main__':
    import sys
    # make_relationship_index()
    print Page.find('GersonGreene').generate_ancestors_compact_html()
