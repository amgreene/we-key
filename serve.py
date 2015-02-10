from fwpage import Page, locate_image, make_index, make_relationship_index, html_index_images
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

@app.route("/index/images")
def serve_image_list():
    csslink = '<link rel="stylesheet" type="text/css" href="static/g.css">'
    csslink += '<script src="//use.edgefonts.net/alegreya;shanti.js"></script>'
    return csslink + html_index_images()

@app.route("/img/<key>")
def serve_image(key):
    return send_file(locate_image(key))

@app.route("/<name>")
def do_name(name):
    csslink = '<link rel="stylesheet" type="text/css" href="static/g.css">'
    csslink += '<script src="//use.edgefonts.net/alegreya;shanti.js"></script>'
    page = Page.find(name)
    return (csslink + 
            page.turn_page_into_html() +
            "<hr>Tools: <a target='_blank' href='/reindex'>Re-index</a>"
        )

if __name__ == "__main__":
    app.run()
