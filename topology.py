import argparse
import json
import logging
import re
from flask import render_template, Flask
import cobra.mit.session
import cobra.mit.access
from requests.packages.urllib3 import disable_warnings

disable_warnings()
app = Flask(__name__, template_folder="templates")

class Leaf(object):
    def __init__(self,id, name):
        self.id = int(id)
        self.name = name
        self.apics = []
        self.fexes = []
        self.vmms = []
        self.spines = []

    def __repr__(self):
        return """{}

        Spines:
            {}

        APICs:
            {}

        VMMs:
            {}

        Fexes:
            {}""".format(self.name, self.spines, self.apics, self.vmms, self.fexes)


class Fex(object):
    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return self.id


class APIC(object):
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return self.name


class Spine(object):
    def __init__(self, id, name):
        self.id = int(id)
        self.name = name

    def __repr__(self):
        return self.name


class VMM(object):
    def __init__(self, id, name):
        self.id = int(id)
        self.name = name

    def __repr__(self):
        return self.name

def get_mo_directory_with_user(apic, user, password):
    ls = cobra.mit.session.LoginSession('https://{}'.format(apic), user, password, timeout=1000)
    md = cobra.mit.access.MoDirectory(ls)
    md.login()
    return md

def get_topology(apic, username, password):
    md = get_mo_directory_with_user(apic, username, password)

    leafs = {}
    apics = {}
    spines = {}

    fabric_nodes = md.lookupByClass('fabricNode')

    for node in fabric_nodes:
        if node.role == 'leaf':
            leafs[node.id] = Leaf(node.id, node.name)
            fexes = md.lookupByClass('eqptExtCh', parentDn=node.dn)
            for fex in fexes:
                leafs[node.id].fexes.append(Fex('{}:{}'.format(node.id, fex.id)))
        elif node.role == 'spine':
            spines[node.id] = Spine(node.id, node.name)
        elif node.role == 'controller':
            apics[node.id] = APIC(node.id, node.name)

    links = md.lookupByClass('fabricLink')
    adjacencies = md.lookupByClass('hvsAdj')

    for link in links:
        if leafs.get(link.n1, None):
            try:
                spine = spines[link.n2]
                if spine not in leafs[link.n1].spines:
                    leafs[link.n1].spines.append(spine)
            except KeyError:
                pass

            try:
                apic = apics[link.n2]
                if apic not in leafs[link.n1].apics:
                    leafs[link.n1].apics.append(apic)
            except KeyError:
                pass

    vcenters = {}
    for adj in adjacencies:
        if adj.nbrDesc != '':
            leaf = adj.nbrDesc.rsplit('/', 1)[1].rsplit('-', 1)

            vcenter = re.findall(r'\[([\w-]+)\]', str(adj.dn))[0]

            # esx = md.lookupByDn(adj.parentDn)
            vmm = vcenters.get(vcenter)
            if not vmm:
                vmm = VMM(0, vcenter)
                vcenters[vcenter] = vmm

            if vmm not in leafs[leaf[1]].vmms:
                leafs[leaf[1]].vmms.append(vmm)

    topology = {"nodes": [], "links": []}

    nodes = set()
    links = set()

    for leaf in leafs.values():
        nodes.add((leaf.id, 1))
        for spine in leaf.spines:
            nodes.add((spine.id, 2))
        for vm in leaf.vmms:
            nodes.add((vm.name, 3))
        for fex in leaf.fexes:
            nodes.add((fex.id, 4))

    nodes = list(nodes)

    for leaf in leafs.values():
        source = nodes.index((leaf.id, 1))
        for spine in leaf.spines:
            target = nodes.index((spine.id, 2))
            links.add((source, target, 1, 1))
        for vm in leaf.vmms:
            target = nodes.index((vm.name, 3))
            links.add((source, target, 1, 1))
        for fex in leaf.fexes:
            target = nodes.index((fex.id, 4))
            links.add((source, target, 1, 1))

    topology["nodes"] = [{"name": name, "group": group} for name, group in nodes]
    topology["links"] = [{"source": source, "target": target, "value": value, "weight": weight} for
                         source, target, value, weight in links]

    return topology

@app.route('/topology.json/')
def topology():
    return json.dumps(get_topology(args.url, args.login, args.password))


@app.route('/')
def home():
    return render_template('topology.html')




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url',
                        help='APIC IP address.')
    parser.add_argument('-l', '--login',
                        help='APIC login ID.')
    parser.add_argument('-p', '--password')

    args = parser.parse_args()
    # Start Flask server
    app.run(debug=True, use_reloader=True)
