from fwpage import Page, make_index, make_relationship_index
from flask import Flask
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
