"""
Python implementation of Numbo
Based on reading in _Fluid Concepts and Creative Analogies_
"""

import functools
import random

from gvanim import Animation, render, gif

from coderack import Rack
from coderack import RackUrgency
from network import Network, LinkDirection, NetworkLink, NetworkNode, ActivationLevel


# Initialize PNet
class NumboNodeType:
    TARGET = "target"
    SECONDARY = "secondary target"
    BRICK = "brick"
    BLOCK = "block"
    OPERATION = "operation"


class NumboCytoNode:
    def __init__(self, label, ntype, networkNode=None):
        self.label = label
        self.ntype = ntype
        self.pnetNode = networkNode
        self.status = "free"
        self.links = []
        self.attractiveness = 0
        self.secondary = None

        # TODO: Should this just be the weight/activation level?
        self.attractiveness = 1

    def add_link(self, link):
        self.links.append(link)
        if link.direction == LinkDirection.BIDIRECTIONAL:
            # TODO: This seems fragile, as we may add new fields
            link.node2.links.append(NetworkLink(link.node2, self, relationship=link.relationship, weight=link.weight))

    def linked_node_strings(self):
        return list(map(lambda x: str(x.node2), self.links))

    def __str__(self):
        selfstr = ""
        if self.ntype == NumboNodeType.OPERATION:
            selfstr += "(" + self.label.join(self.linked_node_strings()) + ")"
        else:
            selfstr = self.ntype + "." + self.status + ":" + self.label + "<" + str(
                self.pnetNode.activation if self.pnetNode else None) + ">"
            if self.ntype == NumboNodeType.BLOCK:
                selfstr = "[" + selfstr
                for l in self.links:
                    selfstr += "=" + str(l.node2)
                selfstr += "]"
        return selfstr

    def ga_label(self):
        return self.label + ":" + self.ntype + "[" + self.status + "]:" + str(self.attractiveness)


class Cytoplasm:
    def __init__(self, coderack):
        self.items = []
        self.rack = coderack
        self.ga = None
        self.done = False

        # the higher the temperature, the more likely
        # the execution of "destructive" codelets
        self.temperature = 50

    def enable_animation(self):
        self.ga = Animation()

    def append(self, item):
        if self.ga:
            self.ga.add_node(item)
            self.ga.label_node(item, item.ga_label())
            self.ga.next_step()
        return self.items.append(item)

    def extend(self, items):
        for item in items:
            self.append(item)
        return self

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def step_attractiveness(self):
        codelets = []
        for c in self.items:
            if c.ntype == NumboNodeType.BLOCK and c.attractiveness > 0 and c.status == 'free':
                c.attractiveness -= 1
                if self.ga:
                    self.ga.label_node(c, c.ga_label())
        # TODO: Be more consistent in who can add codelets
        return codelets

    def decrease_temp(self, decrease=1):
        self.temperature -= decrease
        if self.temperature < 0:
            print "\tWARNING: temperature has gone below 0, are we not done?"
            #            assert False
            self.temperature = 0
        return []

    def increase_temp(self, increase=1):
        self.temperature += increase
        if self.temperature > 100:
            print "\tWARNING: temperature has gone above 100, let's do some stuff"
            self.temperature = 100
            rack.add(functools.partial(codelet_propose_destruction, cytoplasm=self), RackUrgency.HIGH)
        else:
            return []

    def clear(self):
        del self.items[:]

    def find_by_type(self, allowed_types=[NumboNodeType.BLOCK, NumboNodeType.BRICK], allowed_status=['free']):
        return filter(lambda x: x.ntype in allowed_types and x.status in allowed_status, self.items)

    def find_exact(self, label, allowed_types=['block', 'brick']):
        for elem in self.items:
            if elem.label == label and elem.ntype in allowed_types:
                print "\tFound exact of " + label + " in cytoplasm"
                if elem.status == "free":
                    return elem
                else:
                    print "\tBut it is not free..."
        return None

    def find_near(self, label, allowed_types=['block', 'brick']):
        for elem in self:
            try:
                if elem.ntype in allowed_types and elem.pnetNode.has_link_to(label, "similar"):
                    print "\tFound one near of " + label + " in cytoplasm: " + elem.label
                    if elem.status == "free":
                        return elem
                    else:
                        print "\tBut it is not free..."
                        # if elem.ntype in allowed_types and (int(elem.label) == int(label) + 1 or int(elem.label) == int(label) - 1):
            except AttributeError:
                print "\tHad issues with pNetNode for: " + str(elem)
        return None

    def debug(self):
        print "CYTOPLASM: TEMP=" + str(self.temperature)
        for p in cytoplasm:
            if p.status != 'taken':
                print p

    def create_block(self, op, result, node1, node2, pnet=None):
        # TODO: This codelet should actually determine if we *want* to create this block
        # e.g. will it get us closer to the goal (or even match the goal)
        node1.status = 'taken'
        node2.status = 'taken'
        pNode = pnet.getNode(str(result))

        cNode = NumboCytoNode(str(result), NumboNodeType.BLOCK, networkNode=pNode)
        codelets = [[functools.partial(codelet_match_target, cNode), RackUrgency.HIGHEST]]
        if str(result) == numboinput['target']:
            self.done = True
        if not pNode:
            codelets.append([functools.partial(codelet_find_syntactically_similar, cNode), RackUrgency.MID])
        else:
            codelets.extend(pNode.activate(level=ActivationLevel.MID))
        cOpNode = NumboCytoNode(op, NumboNodeType.OPERATION)
        cOpNode.add_link(NetworkLink(cOpNode, node1, direction=LinkDirection.UNIDIRECTIONAL))
        cOpNode.add_link(NetworkLink(cOpNode, node2, direction=LinkDirection.UNIDIRECTIONAL))
        cNode.add_link(NetworkLink(cNode, cOpNode, direction=LinkDirection.UNIDIRECTIONAL))


        # TODO: This should actually be related to how "excited" we were to create
        # this block. e.g. if it was the result of an activation vs a random op
        cNode.attractiveness = int(result)

        if self.ga:
            self.ga.add_node(cOpNode)
            self.ga.label_node(cOpNode, cOpNode.label)
            self.ga.add_edge(cOpNode, node1)
            self.ga.add_edge(cOpNode, node2)
            self.ga.add_edge(cNode, cOpNode)
        self.append(cNode)

        self.decrease_temp(decrease=20)

        return codelets

    def destroy_block(self, node, pnet=None):
        # blocks are node->op->*node
        print "CYTOPLASM: Destroying " + str(node)
        codelets = []

        if node.ntype == NumboNodeType.BLOCK:
            self.decrease_temp(decrease=20)
            for l in node.links:
                n = l.node2
                if n.ntype == NumboNodeType.OPERATION:
                    for l2 in n.links:
                        l2.node2.status = 'free'
                        if self.ga:
                            self.ga.remove_edge(n, l2.node2)
                            self.ga.label_node(l2.node2, l2.node2.ga_label())
                        codelets.extend(pnet.activate(l2.node2.label, level=ActivationLevel.LOW))
                    if self.ga:
                        self.ga.remove_node(n)

        # self.items.remove(node)
        self.items = filter(lambda x: x is not node, self.items)
        if self.ga:
            self.ga.remove_node(node)
        node.status = 'destroyed'
        if node.secondary and len(node.secondary):
            for secondary in node.secondary:
                if self.ga:
                    self.ga.remove_node(secondary)
                self.items = filter(lambda x: x is not secondary, self.items)
                secondary.status = 'destroyed'
            node.secondary = None

        if self.ga:
            self.ga.next_step()
        return codelets

# TODO: Load these in as "facts" via JSON/YAML/whatever
def initPnet():
    pnet = Network()
    pnet.ga = Animation()
    # Add our small numbers
    one = pnet.addNode(label="1", top=True)
    two = pnet.addNode(label="2", top=True)
    three = pnet.addNode(label="3", top=True)
    four = pnet.addNode(label="4", top=True)
    five = pnet.addNode(label="5", top=True)
    six = pnet.addNode(label="6", top=True)
    seven = pnet.addNode(label="7", top=True)
    eight = pnet.addNode(label="8", top=True)
    nine = pnet.addNode(label="9", top=True)
    ten = pnet.addNode(label="10", top=True)
    eleven = pnet.addNode(label="11", top=True)
    twelve = pnet.addNode(label="12", top=True)
    pnet.addNode(label="20", top=True)
    pnet.addNode(label="30", top=True)
    pnet.addNode(label="40", top=True)
    pnet.addNode(label="50", top=True)
    pnet.addNode(label="60", top=True)
    pnet.addNode(label="70", top=True)
    pnet.addNode(label="80", top=True)
    pnet.addNode(label="90", top=True)
    pnet.addNode(label="100", top=True)

    # -------
    # These are relationships
    # if we don't make those top level, we need to make sure to pass them in
    requires = pnet.addNode("requires", top=True, activation=ActivationLevel.MID, fixed=True)
    isrequired = pnet.addNode("isrequired", top=True, activation=ActivationLevel.MID, fixed=True)
    produces = pnet.addNode("produces", top=True, activation=ActivationLevel.MID,
                            fixed=True)  # does this make sense to do vs just saying we require these nodes
    isproduced = pnet.addNode("isproduced", top=True, activation=ActivationLevel.MID,
                              fixed=True)  # does this make sense to do vs just saying we require these nodes

    inheritnode = pnet.addNode("inherits", top=True, activation=ActivationLevel.LOW, fixed=True)
    similar = pnet.addNode("similar", top=True, activation=ActivationLevel.MID, fixed=True)
    # end relationships




    # TODO: Should we have a special way of defining quantity?


    for a in range(1, 11):
        node = pnet.getNode(str(a))
        if not node:
            node = pnet.addNode(label=str(a))
        for b in range(a, 11):
            bnode = pnet.getNode(label=str(b))
            if not bnode:
                bnode = pnet.addNode(label=str(b))
            if b == (a + 1) and not node.has_link_to(bnode.label, similar):
                node.add_link(NetworkLink(node, bnode, direction=LinkDirection.BIDIRECTIONAL, relationship=similar))

            pnet_add_add_facts(a, b, bnode, node, pnet)

            # SUBTRACTION
            # if b - a > 0:
            #    pnet_add_sub_facts(a, b, bnode, difference, minuend, node, pnet, subtraction, subtrahend)

            # MULTIPLICATION
            if a > 1 and b > 1:
                pnet_add_mult_facts(a, b, bnode, node, pnet)

    # salient
    # pnet_add_salient_facts(multiplication, multopt, multresult, pnet)

    return pnet


def pnet_add_salient_facts(multiplication, multopt, multresult, pnet):
    result = pnet.getNode("100")
    node = pnet.getNode("5")
    bnode = pnet.getNode("20")
    times = NetworkNode("* (to) 100", parent_type=multiplication, long_desc=(node.label + "*" + bnode.label))
    pnet.addNode(times, False)
    result.add_link(
        NetworkLink(result, times, direction=LinkDirection.BIDIRECTIONAL, relationship=multresult))
    times.add_link(
        NetworkLink(times,
                    node,  # NetworkNode(node.label, parent_type=node),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=multopt))
    times.add_link(
        NetworkLink(times,
                    bnode,  # NetworkNode(bnode.label, parent_type=bnode),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=multopt))


def pnet_add_add_facts(a, b, bnode, node, pnet):
    # Addition is a "concept" here
    addopt = pnet.getNode("additive operand", create=False)
    if not addopt:
        addopt = pnet.addNode("additive operand", activation=ActivationLevel.MID)

    thesum = pnet.getNode("sum", create=False)
    if not thesum:
        thesum = pnet.addNode("sum", activation=ActivationLevel.MID)

    requires = pnet.getNode("requires", create=True)

    produces = pnet.getNode("produces", create=True)
    isrequired = pnet.getNode("isrequired", create=True)
    isproduced = pnet.getNode("isproduced", create=True)
    addition = pnet.getNode("addition", create=False)
    if not addition:
        addition = pnet.addNode("addition", top=True)
        addition.add_codelet(functools.partial(codelet_propose_operation, codelet_operation_add), children_only=True)
        # TODO: Should we have a special way of defining quantity?
        addition.add_link(NetworkLink(addition, addopt, direction=LinkDirection.BIDIRECTIONAL, relationship=requires,
                                      inverse=isrequired))
        addition.add_link(NetworkLink(addition, addopt, direction=LinkDirection.BIDIRECTIONAL, relationship=requires,
                                      inverse=isrequired))
        addition.add_link(NetworkLink(addition, thesum, direction=LinkDirection.BIDIRECTIONAL, relationship=produces,
                                      inverse=isproduced))


    # ADDITION
    sum = pnet.getNode(str(a + b))
    if not sum:
        sum = pnet.addNode(str(a + b))

    # create the instance of addition for these numbers
    plus = NetworkNode(str(a) + "+" + str(b), parent_type=addition, long_desc=(node.label + "+" + bnode.label))
    pnet.addNode(plus, top=False)
    # TODO: There is a lot of redundancy in how links get added
    sum.add_link(NetworkLink(sum, plus, direction=LinkDirection.BIDIRECTIONAL, relationship=thesum))
    # TODO: Should these be bi-directional here?
    # Note that we are actually creating *instances* of the actual "ideal" type of the number
    plus.add_link(
        NetworkLink(plus,
                    node,  # NetworkNode(node.label, parent_type=node),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=addopt))
    plus.add_link(
        NetworkLink(plus,
                    bnode,  # NetworkNode(bnode.label, parent_type=bnode),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=addopt))


def pnet_add_sub_facts(a, b, bnode, difference, minuend, node, pnet, subtraction, subtrahend):
    # Subtraction
    minuend = pnet.getNode("minuend", create=True)
    subtrahend = pnet.getNode("subtrahend", create=True)
    difference = pnet.getNode("difference", create=True)
    subtraction = pnet.getNode("subtraction", create=False)
    requires = pnet.getNode("requires", create=True)
    produces = pnet.getNode("produces", create=True)
    if not subtraction:
        subtraction = pnet.addNode("subtraction", top=True)
        subtraction.add_codelet(functools.partial(codelet_propose_operation, codelet_operation_subtract),
                                children_only=True)
        subtraction.add_link(
            NetworkLink(subtraction, minuend, direction=LinkDirection.UNIDIRECTIONAL, relationship=requires))
        subtraction.add_link(
            NetworkLink(subtraction, subtrahend, direction=LinkDirection.UNIDIRECTIONAL, relationship=requires))
        subtraction.add_link(
            NetworkLink(subtraction, difference, direction=LinkDirection.UNIDIRECTIONAL, relationship=produces))

    diff = pnet.getNode(str(b - a))
    if not diff:
        diff = pnet.addNode(str(b - a))

    # create the instance of addition for these numbers
    minus = NetworkNode(str(b) + "-" + str(a), parent_type=subtraction, long_desc=(bnode.label + "-" + node.label))
    pnet.addNode(minus, False)
    # TODO: There is a lot of redundancy in how links get added
    diff.add_link(NetworkLink(diff, minus, direction=LinkDirection.BIDIRECTIONAL, relationship=difference))
    # TODO: Should these be bi-directional here?
    # Note that we are actually creating *instances* of the actual "ideal" type of the number
    minus.add_link(
        NetworkLink(minus,
                    bnode,  # NetworkNode(bnode.label, parent_type=bnode),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=minuend))
    minus.add_link(
        NetworkLink(minus,
                    node,  # NetworkNode(node.label, parent_type=node),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=subtrahend))


def pnet_add_mult_facts(a, b, bnode, node, pnet):
    multopt = pnet.getNode("multiplicative operand", create=False)
    if not multopt:
        multopt = pnet.addNode("multiplicative operand", activation=ActivationLevel.MID)
    multresult = pnet.getNode("multiplicative result", create=False)
    if not multresult:
        multresult = pnet.addNode("multiplicative result", activation=ActivationLevel.MID)


    requires = pnet.getNode("requires")
    produces = pnet.getNode("produces")
    isrequired = pnet.getNode("isrequired", create=True)
    isproduced = pnet.getNode("isproduced", create=True)
    multiplication = pnet.getNode("multiplication", create=False)
    if not multiplication:
        multiplication = pnet.addNode("multiplication", top=True)
        multiplication.add_codelet(functools.partial(codelet_propose_operation, codelet_operation_multiply),
                                   children_only=True)
        multiplication.add_link(
            NetworkLink(multiplication, multopt, direction=LinkDirection.BIDIRECTIONAL, relationship=requires,
                        inverse=isrequired))
        multiplication.add_link(
            NetworkLink(multiplication, multopt, direction=LinkDirection.UNIDIRECTIONAL, relationship=requires,
                        inverse=isrequired))
        multiplication.add_link(
            NetworkLink(multiplication, multresult, direction=LinkDirection.UNIDIRECTIONAL, relationship=produces,
                        inverse=isproduced))

    # TODO: Should we have a special way of defining quantity?

    result = pnet.getNode(str(a * b))
    if not result:
        result = pnet.addNode(str(a * b))
    times = NetworkNode(str(a) + "*" + str(b), parent_type=multiplication, long_desc=(node.label + "*" + bnode.label))
    pnet.addNode(times, False)
    result.add_link(
        NetworkLink(result, times, direction=LinkDirection.BIDIRECTIONAL, relationship=multresult))
    times.add_link(
        NetworkLink(times,
                    node,  # NetworkNode(node.label, parent_type=node),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=multopt))
    times.add_link(
        NetworkLink(times,
                    bnode,  # NetworkNode(bnode.label, parent_type=bnode),
                    direction=LinkDirection.BIDIRECTIONAL,
                    relationship=multopt))


def codelet_read_target(vision, pnet=None, cytoplasm=None):
    """
    Take in the 'target' item, adding it to the cytoplasm.
    Will likely lead to activation of nodes related to the number based on its size
    For example, a larger number would lead to activation of "multiplication", which
    itself would likely activate codelets which can perform multiplication
    :param vision:
    :param pnet:
    :param ext_cytoplasm:
    :return:
    """
    print "CODELET: read_target"
    t = vision['target']
    pNode = pnet.getNode(t)
    cNode = NumboCytoNode(t, NumboNodeType.TARGET, networkNode=pNode)
    codelets = []
    if pNode:
        codelets.extend(pNode.activate(level=ActivationLevel.HIGH))
    else:
        codelets.append([functools.partial(codelet_find_syntactically_similar, cNode), RackUrgency.MID])

    cytoplasm.append(cNode)
    if int(t) > 20:
        codelets.extend(pnet.activate("multiplication", level=ActivationLevel.HIGH))
    else:
        codelets.extend(pnet.activate("addition", level=ActivationLevel.HIGH))
        codelets.extend(pnet.activate("subtraction", level=ActivationLevel.HIGH))

    return codelets


def codelet_read_brick(vision, pnet=None, cytoplasm=None):
    print "CODELET: read_brick"
    bricks = vision['bricks']
    codelets = []
    if len(bricks):
        b = bricks.pop(random.randint(0, len(bricks)-1))
        pNode = pnet.getNode(b)
        cNode = NumboCytoNode(b, NumboNodeType.BRICK, networkNode=pNode)
        cNode.attractiveness = int(b)
        if pNode:
            codelets.extend(pNode.activate(level=ActivationLevel.HIGH))
        else:
            codelets.append([functools.partial(codelet_find_syntactically_similar, cNode), RackUrgency.MID])

        cytoplasm.append(cNode)

    return codelets


def codelet_seek_reasonable_fascimile(desired, proposed, new_partials, pnet=None, cytoplasm=None, attempt=1):
    """
    Try to locate free Cyto nodes which are reasonably close
    to the given targets, and if available, push the next
    set of codelets
    desired - array of labels of nodes we would like to find (as numbers)
    proposed - the label for the item we plan on creating
    new_partials - the codelets that will get run if we succeed
    :return:
    """
    print "CODELET: seek_reasonable_fascimile: " + str(desired) + " ATTEMPT: " + str(attempt)
    assert len(desired) > 1

    found = []
    for des in desired:
        node = cytoplasm.find_exact(des)
        if node is None or node in found:
            node = cytoplasm.find_near(des)

            if node is None or node in found:
                print "\tUnable to find anything similar to " + des
                break
            else:
                found.append(node)
                node.status = 'pending'

        else:
            found.append(node)
            node.status = 'pending'

    returned = []
    for n in found:
        n.status = 'free'
    if len(found) == len(desired):
        # If we are here, we now have found all of our desired nodes
        # partials would be codelet_create_block()

        cytoplasm.decrease_temp()

        for codelet in new_partials:
            # this assumes our partials take positional arguments corresponding to what we found
            returned.append(functools.partial(codelet, *found))

    else:
        cytoplasm.increase_temp()
        if attempt < 2:
            # Give it another shot... maybe this is more about reducing urgency?
            returned.append(functools.partial(codelet_seek_reasonable_fascimile, desired, proposed, new_partials,
                                              attempt=attempt + 1))

    return returned


def codelet_create_secondary_target(elem, cytoplasm=None, pnet=None):
    print "CODELET: create_secondary_target"
    target = int(numboinput['target'])
    codelets = []
    # TODO: Should the block have a link to its secondary so we can destroy it?
    if elem.ntype is NumboNodeType.BLOCK and elem.status == 'free':
        elemval = int(elem.label)
        delta = elemval - target
        if delta < 0:
            delta = -delta
        pNode = pnet.getNode(str(delta))
        cNode = NumboCytoNode(str(delta), NumboNodeType.SECONDARY, networkNode=pNode)
        cytoplasm.append(cNode)
        elem.secondary = [cNode]
        print "\tCreated SECONDARY target with value " + str(delta)
        if pNode:
            codelets.extend(pNode.activate(level=ActivationLevel.MID))

        if elemval > target and elemval % target == 0:
            pNode = pnet.getNode(str(elemval / target))
            cNode = NumboCytoNode(str(elemval / target), NumboNodeType.SECONDARY, networkNode=pNode)
            cytoplasm.append(cNode)
            elem.secondary.append(cNode)
        elif target > elemval and target % elemval == 0:
            pNode = pnet.getNode(str(target / elemval))
            cNode = NumboCytoNode(str(target / elemval), NumboNodeType.SECONDARY, networkNode=pNode)
            cytoplasm.append(cNode)
            elem.secondary.append(cNode)

    return codelets


def codelet_match_target(block, cytoplasm=None, pnet=None):
    print "CODELET: match_target"

    codelets = []

    item = cytoplasm.find_exact(block.label, allowed_types=[NumboNodeType.TARGET, NumboNodeType.SECONDARY])
    if item and item.ntype == NumboNodeType.TARGET:
        # TODO: We should perhaps just have access to the rack and clear it
        print "Found solution!"
        print str(item)
        cytoplasm.done = True
    elif item and item.ntype == NumboNodeType.SECONDARY:
        block.attractiveness += 10
        if item.pnetNode:
            codelets.extend(item.pnetNode.activate(level=ActivationLevel.MID))
        cytoplasm.destroy_block(item, pnet=pnet)
    else:
        # See if it matches a secondary target
        return [[functools.partial(codelet_create_secondary_target, block), RackUrgency.HIGH]]
    return codelets


def codelet_find_syntactically_similar(needle, pnet=None, cytoplasm=None):
    """
    Identify PNet nodes which are "similar" to the given number
    """
    print "CODELET: find_similar: " + str(needle)
    if type(needle) is str:
        as_str = needle
    elif type(needle) is int:
        as_str = str(needle)
    else:
        as_str = needle.label
    the_len = len(as_str)
    # if we don't have it, then likely it is bigger than our low
    # numbers, so let's "reduce" it, first by converting it into a base number
    i = 0
    new_val = ""
    for c in as_str:
        if i == 0:
            new_val = c
        else:
            new_val += "0"
        i += 1

    print "\tPerhaps " + new_val + " is available?"
    codelets = []
    similar = pnet.getNode(new_val)
    if similar:
        # TODO: do this as a codelet
        codelets.extend(similar.activate(level=ActivationLevel.LOW))
        print "\t" + str(type(needle))
        needle.pnetNode = similar
    # assert similar

    return codelets


def codelet_destroy_block(todestroy, pnet=None, cytoplasm=None):
    print "CODELET: destroy_block " + str(todestroy)
    if todestroy.status == 'free':
        cytoplasm.destroy_block(todestroy, pnet=pnet)

    return None


def codelet_propose_destruction(pnet=None, cytoplasm=None):
    """
    Will attempt to destroy a block that has been created
    TODO: Should the urgency of this factor in whether or not we will *always* do it?
    :param pnet:
    :param cytoplasm:
    :return:
    """
    print "CODELET: propose_destruction"
    proposed = None
    for block in cytoplasm:
        if block.status == 'free' and block.ntype == NumboNodeType.BLOCK:
            if not proposed or proposed.attractiveness < block.attractiveness:
                proposed = block

    if proposed:
        print "\tFound a block to destroy: " + str(proposed)
        return [functools.partial(codelet_destroy_block, proposed)]
    else:
        print "\tNo block"


def codelet_propose_random_operation(pnet=None, cytoplasm=None):
    print "CODELET: propose_random_operation"

    nodes = []
    noderack = Rack()
    for c in cytoplasm:
        if c.ntype in [NumboNodeType.BLOCK, NumboNodeType.BRICK] and c.status == 'free' and c.attractiveness > 0:
            noderack.add(c, c.attractiveness)

    if random.randint(1, 100) < 30:
        codelets = [[codelet_propose_random_operation, RackUrgency.MICRO]]
    else:
        codelets = []
    if len(noderack) >= 2:
        n1 = noderack.take()
        n2 = noderack.take()
        if int(n1.label) > int(n2.label):
            nodes.append(n1)
            nodes.append(n2)
        else:
            nodes.append(n2)
            nodes.append(n1)

        # pick a random operation
        # TODO: After picking 2 items, should we pick the operation
        # based on the ones that would most apply to these selections
        addition = pnet.getNode("addition")

        mult = pnet.getNode("multiplication")
        sub = pnet.getNode("subtraction")
        oprack = Rack()

        if mult and n1.label != '1' and n2.label != '1':
            oprack.add(mult, mult.activation)

        if sub:
            oprack.add(sub, sub.activation)

        if addition:
            oprack.add(addition, addition.activation)

        op = oprack.take()
        code = None
        # TODO: Should we use the codelets that are associated with this node?
        if op == addition:
            code = codelet_operation_add
        elif op == mult:
            code = codelet_operation_multiply
        elif op == sub:
            code = codelet_operation_subtract

        # TODO: Urgency should depend on how much we want to create the given item
        print "\tFound " + str(n1) + " and" + str(n2) + " to apply operation to"
        codelets.append([functools.partial(code, nodes[0], nodes[1]), RackUrgency.LOW])
    return codelets




def codelet_propose_operation(proposed_op, target_node=None, pnet=None, cytoplasm=None):
    """
    What this node should do is, based on the target node and "this" node
    take the required parameters and put in a codelet to identify blocks or bricks
    which are "similar" to the "inputs" into the operation
    and, if found, put on the codelet which actually does the operation
    :param proposed_op:
    :param target_node: the
    :return:
    """
    print "CODELET: propose_operation from " + target_node.long_desc
    print target_node.link_str()

    # Fetch inputs
    parent = target_node.parent

    usedlinks = []
    inputs = []
    produces = None
    for l in parent.links:
        if str(l.relationship) == 'requires':
            needed = l.node2.label
            links = target_node.find_links(needed)
            found = False
            if links:
                for nl in links:
                    if nl not in usedlinks:
                    # if nl.node2 not in inputs:
                    inputs.append(nl.node2)
                    usedlinks.append(nl)
                    found = True
                    #break
                if not found:
                    print "\tERROR: all " + needed + " already used or not found"
                    cytoplasm.increase_temp()
                    return None
            else:
                print "\tERROR: Unable to find " + needed
                assert False
        if str(l.relationship) == 'produces':
            needed = l.node2.label
            links = target_node.find_links(needed)
            if links:
                for nl in links:
                    produces = nl.node2.label
                    break
            else:
                print "\tERROR: Unable to find " + needed
                return None

    codelets = []
    inputs = list(map(lambda x: x.label, inputs))
    print "\tAdding codelet seek_reasonable_fascimile of " + str(inputs)

    fasc = [functools.partial(codelet_seek_reasonable_fascimile, inputs, produces, [proposed_op]), RackUrgency.LOW]
    codelets.append(fasc)
    return codelets


def codelet_create_block(oplabel, resultlabel, node1, node2, pnet=None, cytoplasm=None):
    print "CODELET: create_block: " + str(resultlabel)

    if node1.status == 'free' and node2.status == 'free':
        return cytoplasm.create_block(oplabel, resultlabel, node1, node2, pnet=pnet)
    return None


def codelet_operation_multiply(node1, node2, pnet=None, cytoplasm=None):
    print "CODELET: operation_multiply: " + node1.label + "*" + node2.label
    if node1.label == "1" or node2.label == "1":
        return None
    if node1.status == 'free' and node2.status == 'free':
        a = int(node1.label)
        b = int(node2.label)
        c = a * b

        # figure out our urgency based on how close this gets us to something we want
        mindelta = 100000
        for node in cytoplasm:
            if node.ntype in [NumboNodeType.TARGET, NumboNodeType.SECONDARY]:
                delta = abs(int(node.label) - c)
                if delta < mindelta:
                    mindelta = delta

        urgency = RackUrgency.LOW
        if mindelta <= 10:
            urgency = RackUrgency.HIGH
        elif mindelta <= 20:
            urgency = RackUrgency.LOW
        elif mindelta <= 100:
            urgency = RackUrgency.MICRO
        else:
            urgency = 1

        print "\tmindelta is " + str(mindelta)

        return [[functools.partial(codelet_create_block, "x", c, node1, node2), urgency]]


def codelet_operation_add(node1, node2, pnet=None, cytoplasm=None):
    print "CODELET: operation_add: " + node1.label + " + " + node2.label
    if node1.status == 'free' and node2.status == 'free':
        a = int(node1.label)
        b = int(node2.label)
        c = a + b

        mindelta = 100000
        for node in cytoplasm:
            if node.ntype in [NumboNodeType.TARGET, NumboNodeType.SECONDARY]:
                delta = abs(int(node.label) - c)
                if delta < mindelta:
                    mindelta = delta

        urgency = RackUrgency.LOW
        if mindelta <= 10:
            urgency = RackUrgency.HIGH
        elif mindelta <= 20:
            urgency = RackUrgency.LOW
        elif mindelta <= 100:
            urgency = RackUrgency.MICRO
        else:
            urgency = 1

        print "\tmindelta is " + str(mindelta)

        return [[functools.partial(codelet_create_block, "+", c, node1, node2), urgency]]


def codelet_operation_subtract(node1, node2, pnet=None, cytoplasm=None):
    print "CODELET: operation_subtract: " + node1.label + " - " + node2.label
    if node1.status == 'free' and node2.status == 'free':
        a = int(node1.label)
        b = int(node2.label)
        c = a - b
        if c > 0:
            mindelta = 100000
            for node in cytoplasm:
                if node.ntype in [NumboNodeType.TARGET, NumboNodeType.SECONDARY]:
                    delta = abs(int(node.label) - c)
                    if delta < mindelta:
                        mindelta = delta

            urgency = RackUrgency.LOW
            if mindelta <= 10:
                urgency = RackUrgency.HIGH
            elif mindelta <= 20:
                urgency = RackUrgency.LOW
            elif mindelta <= 100:
                urgency = RackUrgency.MICRO
            else:
                urgency = 1

            print "\tmindelta is " + str(mindelta)

            return [[functools.partial(codelet_create_block, "-", c, node1, node2), urgency]]
        return None


def debug_network():
    cytoplasm.debug()
    print "RACK LENGTH: " + str(len(rack))


# print "CODERACK"
#    for p in rack:
#        print p


network = initPnet()

# this set of inputs exercises the ability to identify sub-targets based on subtraction
# TODO: Implement a codelet_identify_subtarget

# numboinput = dict(target="114", bricks=["12", "20", "7", "1", "6", "11"])
numboinput = dict(target="11", bricks=["2", "3", "5"])
#numboinput = dict(target="10", bricks=["5", "2", "3"])
rack = Rack()
cytoplasm = Cytoplasm(rack)
cytoplasm.enable_animation()

rack.add(functools.partial(codelet_read_target, numboinput, pnet=network, cytoplasm=cytoplasm), RackUrgency.HIGH)
for x in range(0, len(numboinput['bricks'])):
    rack.add(functools.partial(codelet_read_brick, numboinput, pnet=network, cytoplasm=cytoplasm), RackUrgency.MID)

debug_network()
# Here starts our main run loop, which should probably get encapsulated
steps = 0
while len(rack) > 0 and steps < 150 and not cytoplasm.done:
    print "****" + str(steps) + "****"
    codelet = rack.take()
    new_codelets = codelet()

    if not new_codelets:
        new_codelets = []
    if steps % 10 == 0 and steps > 1:
        # arbitrary and non-random
        for brick in cytoplasm.find_by_type(allowed_types=[NumboNodeType.TARGET, NumboNodeType.BRICK]):
            new_codelets.extend(brick.pnetNode.activate(level=ActivationLevel.MID))

    if steps % 10 == 0 and steps > 0:
        network.step_activation()
    # TODO: this should likely be a set of tuples of (codelet, urgency)
    # or perhaps we just give each codelet access to the rack
    if new_codelets is not None and len(new_codelets) > 0:
        for c in new_codelets:
            urgency = RackUrgency.LOW
            if type(c) is list:
                urgency = c[1]
                c = c[0]
            rack.add(functools.partial(c, pnet=network, cytoplasm=cytoplasm), urgency)

    cytoplasm.step_attractiveness()
    debug_network()
    steps += 1

    if steps > 5 and len(cytoplasm.find_by_type()) < 2:
        rack.add(functools.partial(codelet_propose_destruction, pnet=network, cytoplasm=cytoplasm), RackUrgency.LOW)

    if len(rack) < 2:
        if steps >= len(numboinput['bricks']) and len(
                cytoplasm.find_by_type(allowed_types=[NumboNodeType.BLOCK], allowed_status=['free', 'taken'])) < 1:
            rack.add(functools.partial(codelet_propose_random_operation, pnet=network, cytoplasm=cytoplasm),
                     RackUrgency.LOW)
    if steps > 20:
        if cytoplasm.temperature < 10 and len(rack) < 2:
            rack.add(functools.partial(codelet_propose_destruction, pnet=network, cytoplasm=cytoplasm), RackUrgency.MID)
        elif cytoplasm.temperature >= 30 and len(rack) < 2:
            rack.add(functools.partial(codelet_propose_random_operation, pnet=network, cytoplasm=cytoplasm),
                     RackUrgency.MID)

print "DONE? " + str(cytoplasm.done)

if cytoplasm.ga:
    graphs = cytoplasm.ga.graphs()
    files = render(graphs, 'renders/cytoplasm', 'png')
    gif(files, 'renders/cytoplasm', 250)

if network.ga:
    graphs = network.ga.graphs()
    files = render(graphs, 'renders/network', 'png')
    gif(files, 'renders/network', 250)
