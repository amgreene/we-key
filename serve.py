from fwpage import *
from flask import Flask, send_file
app = Flask(__name__)
app.debug = True


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/favicon.ico")
def faviconx():
    return ''


@app.route("/reindex")
def reindex():
    make_index()
    make_relationship_index()
    return 'Indexed.'


@app.route("/index/tags")
def serve_tags_list():
    csslink = '<link rel="stylesheet" type="text/css" href="/static/g.css">'
    csslink += '<script src="//use.edgefonts.net/alegreya;shanti.js"></script>'
    return csslink + html_index_tags()


@app.route("/index/images")
def serve_image_list():
    csslink = '<link rel="stylesheet" type="text/css" href="/static/g.css">'
    csslink += '<script src="//use.edgefonts.net/alegreya;shanti.js"></script>'
    return csslink + html_index_images()


@app.route("/img/<key>")
def serve_image(key):
    from images import find_image_by_hashlet, get_abs_image_path
    # first assume the key is a hashlet
    (full_hash, rel_path) = find_image_by_hashlet(key)
    # if that doesn't work, see if it's an alias
    if not rel_path:
        rel_path = locate_image(key)
        if not rel_path:
            abort(404)
    abs_path = get_abs_image_path(rel_path)
    return send_file(abs_path)


@app.route("/<name>")
def do_name(name):
    page = Page.find(name)
    return page.turn_page_into_html()


if __name__ == "__main__":
    app.run()
