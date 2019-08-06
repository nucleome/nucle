
import falcon
import h5py
import json
import numpy as np
import sys

from io import StringIO 
# Falcon follows the REST architectural style, meaning (among
# other things) that you think in terms of resources and state
# transitions, which map to HTTP verbs.
import multiprocessing
import argparse

import gunicorn.app.base

from gunicorn.six import iteritems

def help():
    return "hss to microservice[TODO]"
def set_parser(p):
    p.add_argument('-i','--input',dest='input',default='stdin',type=str,help="input file Default: %(default)s")   
    p.add_argument('-p','--port',dest='port',default=8586,type=int,help="port Default: %(default)s")   
class Genome(object):
    def __init__(self, db):
        self.db = db
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        resp.body = (str(self.db['genome']['assembly'][...]))
class Coord(object):
    def __init__(self,coords):
        self.coords = coords
    def on_get(self,req,resp,i):
        resp.status = falcon.HTTP_200  # This is the default status
        ## coords[i][cell][dimension]
        buf = StringIO()
        buf.write("Structs\t%d\n" % len(self.coords))
        buf.write("Index\t%d\n" % i)
        buf.write("Beads\t%d\n" % len(self.coords[i]))
        for st in self.coords[i]:
            buf.write("%.2f\t%.2f\t%.2f\n" % (st[0],st[1],st[2]))
        resp.body = (buf.getvalue())
class Dimension(object):
    def __init__(self,dim):
        self.dim = dim
    def on_get(self,req,resp):
        buf = StringIO()
        buf.write("nstruct\t%d\n" % self.dim[0])
        buf.write("nbead\t%d\n" % self.dim[1])
        resp.body=(buf.getvalue())
class Array(object):
    def __init__(self,d):
        self.d = d
    def on_get(self,req,resp):
        buf = StringIO()
        for i in self.d:
            buf.write("%.2f\n"%i)
        resp.body=(buf.getvalue())

class SArray(object):
    def __init__(self,d):
        self.d = d
    def on_get(self,req,resp):
        buf = StringIO()
        for i in self.d:
            buf.write("%s\n"%i)
        resp.body=(buf.getvalue())

class IArray(object):
    def __init__(self,d):
        self.d = d
    def on_get(self,req,resp):
        buf = StringIO()
        for i in self.d:
            buf.write("%d\n"%i)
        resp.body=(buf.getvalue())


class nucle3d(object):
    def __init__(self,db):
        self.db = db
        self.coords = np.transpose(db['coordinates'][:],(1,0,2))
        genome = db['genome']
        assembly = genome["assembly"][...]
        self.assembly = str(assembly)
        self.chroms = genome['chroms'][:]
        origins = genome['origins'][:]
        lengths = genome['lengths'][:]

        index = db['index']
        iChrom = index['chrom'][:]
        self.chromSizes = index['chrom_sizes'][:]
        iStart = index['start'][:]
        iEnd = index['end'][:]
        
        self.res = iEnd[2] - iStart[2]  # TODO


    def on_get(self,req,resp,i):
        resp.status = falcon.HTTP_200  # This is the default status
        ## coords[i][cell][dimension]
        resp.append_header('Access-Control-Allow-Origin', 'http://x7.andrew.cmu.edu:8080')
        resp.append_header('Access-Control-Allow-Credentials', 'true')
        buf = StringIO()
        buf.write("TITLE\t%d\n" % i)
        buf.write("GENOME\t%s\n" % self.assembly)
        buf.write("BINSIZE\t%d\n" % self.res)
        k=0
        for i0,st in enumerate(self.chroms):
            buf.write("CHR\t")
            buf.write("%s\n"%str(st.decode("ascii")))
            for j in range(self.chromSizes[i0]):
                st = self.coords[i][k]
                buf.write("%d,%.2f,%.2f,%.2f\n" % (j,st[0],st[1],st[2]))
                k+=1
        resp.body = (buf.getvalue())






# falcon API Generate

def generateApp(filename):
    app = falcon.API()
    db = h5py.File(filename, 'r')
    serv = Genome(db)
    coords = np.transpose(db['coordinates'][:],(1,0,2))
    c = Coord(coords)
    genome = db['genome']
    chroms = genome['chroms'][:]
    origins = genome['origins'][:]
    lengths = genome['lengths'][:]
    servOrigins = IArray(origins)
    servLengths = IArray(lengths)
    servChroms = SArray(chroms)
    print(len(coords),len(coords[0]),len(coords[0][0]))
    app.add_route('/genome', serv)
    app.add_route('/genome/chroms', servChroms)
    app.add_route('/genome/origins', servOrigins)
    app.add_route('/genome/lengths', servLengths)
    app.add_route('/coord/{i:int}',c)
    app.add_route('/dim',Dimension([len(coords),len(coords[0])]))
    app.add_route('/radii',Array(db['radii'][:]))

    index = db['index']
    iChrom = index['chrom'][:]
    app.add_route("/index/chrom",IArray(iChrom))
    iStart = index['start'][:]
    app.add_route("/index/start",IArray(iStart))
    iEnd = index['end'][:]
    app.add_route("/index/end",IArray(iEnd))

    app.add_route("/nucle3d/{i:int}",nucle3d(db))


    return app

class StandaloneApplication(gunicorn.app.base.BaseApplication):
    
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def run(args):
    app = generateApp(args.input)
    options = {
        'bind': '%s:%d' % ('127.0.0.1', args.port),
        'workers': 1,
    }
    StandaloneApplication(app, options).run()

if __name__=="__main__":
    p=argparse.ArgumentParser( description = 'serverhss', epilog='')
    set_parser(p)
    if len(sys.argv)==1:
        print(p.print_help())
        exit(0)
    run(p.parse_args())
