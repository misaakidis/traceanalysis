# coding: utf-8

import argparse
import networkx as nx
import warnings

from connections import Connection, Event

__author__ = "Juliano Fischer Naves"

COMPONENTS_FILE_NAME = "components_log.txt"
CONNECTIONSLOG_FILE_NAME = "connections_out_file.txt"

LARGEST_CONNECTED_COMPONENT_REPORT = "largest_connected_components_report.txt"

NUMBER_OF_CONNECTED_COMPONENTS_REPORT = "number_of_connected_components_report.txt"

CONNECTIONS_DURATION_CDF_REPORT = "connections_duration_pdf_report.txt"

# extracting arguments
parser = argparse.ArgumentParser(description="Descrição")
parser.add_argument("-f", "--file", dest="filename", help="the trace file that will be analyzed", metavar="FILENAME")
parser.add_argument("-n", "--numberOfNodes",dest="numberOfNodes", help="the number of nodes in the network",
                    metavar="NUMBER")
parser.add_argument("-e", "--end", dest="endtime",help="trace ending time", metavar="ENDTIME")
parser.add_argument("-s", "--step", dest="log_step", help="The step for logging component information",
                    metavar="STEP")
args = parser.parse_args()


# connected_components_log_file = open("connected_components_log")


# init global vars
def _init():
    global g, last_file_position, __f, number_of_nodes, endtime, created_connections, \
        open_connections, largest_connected_component, logging_step, last_log, connected_components_log, \
    max_node_degree, list_of_average_node_degrees

    number_of_nodes = int(args.numberOfNodes)

    g = nx.Graph()
    g.add_nodes_from(range(number_of_nodes))

    last_file_position = None

    filename = args.filename
    __f = open(filename)

    # default value is 30
    logging_step = int(args.log_step) if args.log_step else 30

    endtime = int(args.endtime)

    created_connections = []
    open_connections = []
    connected_components_log = {}
    largest_connected_component = 0
    last_log = 0
    max_node_degree = 0;
    list_of_average_node_degrees = []


# convert a trace line to an object of Event
def get_event(line):
    l = line.split()
    d = dict()
    d["from"] = int(l[2])
    d["to"] = int(l[3])
    d["event"] = l[1]
    d["time"] = int(l[0])
    d["status"] = l[4]
    e = Event(d)
    return e


''' initing é inclusivo, ending é exclusivo
def init_graph(initing, ending):
    g.add_nodes_from(range(initing, ending))
'''


# apply and event to the graph (add or remove an edge)
def apply_graph_change(event):
    if event.is_opening():
        g.add_edge(event.from_node, event.to_node)
    else:
        if g.has_edge(event.from_node, event.to_node):
            g.remove_edge(event.from_node, event.to_node)
        else:
            warnings.warn("Trying to remove an inexistent edge")


# e: the event to be processed
def process_event(e):
    apply_graph_change(e)

    # add one connection to open_connections or close the connection
    if e.is_opening():
        c = Connection(e)
        open_connections.append(c)
        created_connections.append(c)
    else:
        # it is a connection closing event
        close_connection(e)


# receives an event and remove a connection from open_connections besides add closing time to the object of Connection
def close_connection(e):
    to_remove = None
    for c in open_connections:
        if c.is_same_connection(e):
            c.end_time = e.time
            to_remove = c
            break
    open_connections.remove(to_remove)


# returns the events of this instant
def get_events_at_instant(time):
    global last_file_position
    last_file_position = __f.tell()
    l = __f.readline().strip()
    _list = []

    # end of the file
    if len(l) == 0:
        return _list

    e = get_event(l)

    # only events of this instant (now)
    while e.time == time:
        _list.append(e)
        last_file_position = __f.tell()
        l = __f.readline().strip()

        # end of the file
        if len(l) == 0:
            break

        e = get_event(l)

    # the last read event occurred after "instant"
    # Moves the file pointer to the last read line
    __f.seek(last_file_position)

    return _list


# run the analysis from begin to ending
def run():
    global largest_connected_component, last_log, max_node_degree, list_of_average_node_degrees

    for instant in range(0, endtime+1):
        events = get_events_at_instant(instant)

        for e in events:
            process_event(e)

        # get the largest_connected_component
        connected_components = nx.connected_components(g)
        largest = max([len(x) for x in connected_components])
        largest_connected_component = largest if largest > largest_connected_component else largest_connected_component

        list_of_connected_components = list(nx.connected_components(g))

        degrees = [g.degree(node) for node in g.nodes()]
        max_node_degree = max(max_node_degree, max(degrees))

        list_of_average_node_degrees.append(sum(degrees)/len(degrees))

        # instant is equivalent to 'now'
        if instant - last_log >= logging_step:
            last_log = instant
            # connected_components_log.append("%d    %s\n" % (instant, str(list_of_connected_components)))
            connected_components_log[instant] = list_of_connected_components

    close_remaining_connections(endtime)
    # perform post processing information extraction
    post_processing()


# setting end time for connections which are not closed at trace ending
def close_remaining_connections(t):
    for c in open_connections:
        c.end_time = t


# perform post processing information extraction
def post_processing():
    # write down the log information
    print("Number of connections: %d" % (get_number_of_connections(),))
    print("Average number of connections (per nodes): %f" % (get_average_number_of_connections(),))
    print("Connections per minute: %f" % (get_connections_per_minute(), ))
    print("Total connection time: %d" % (get_total_connection_time(),))
    print("Average connection time (per connection): %f" % (get_average_connection_time()))
    print("Largest connected component: %d" % (largest_connected_component,))
    print("Average largest connected component %f" % (get_average_largest_connected_component(),))
    print("Median largest connected component %f" % (get_median_largest_connected_component(),))
    print("Average number of connected components %f" % (get_average_number_of_connected_components(),))
    print("Median number of connected components %f" % (get_median_number_of_connected_components(),))
    print("Max node degree: %d" % (max_node_degree,))
    print("Average node degree: %f" % (get_average_node_degree(),))
    do_the_log()


def do_the_log():
    # logging components
    components_file = open(COMPONENTS_FILE_NAME, "w+")
    for key in sorted(connected_components_log):
        components_file.write("%d    %s\n" % (key, str(connected_components_log[key])))

    # logging connections
    connections_out_file = open(CONNECTIONSLOG_FILE_NAME, "w+")
    connections_out_file.writelines([str(c)+"\n" for c in created_connections])

    # largest connected component
    log_largest_connected_component_evolution()

    # number of connected components
    log_number_of_connected_components()

    log_connection_duration_pdf()


# get de average node degree (number of links)
def get_average_node_degree():
    return sum(list_of_average_node_degrees)/len(list_of_average_node_degrees)


# get the total number of connections
def get_number_of_connections():
    return len(created_connections)


# get the average number of connections by node
def get_average_number_of_connections():
    return get_number_of_connections() / number_of_nodes


# get the total connection time - sum of duration of all connections
def get_total_connection_time():
    return sum(c.duration() for c in created_connections)


# get the average connection time  - total_connection_time/total_of_connections
def get_average_connection_time():
    return get_total_connection_time() / get_number_of_connections()


# get the number of connections per minute
def get_connections_per_minute():
    minutes = endtime / 60
    return get_number_of_connections() / minutes


# format: time    largest_connected_component
# output: largest_connected_components_report.txt
def log_largest_connected_component_evolution():
    with open(LARGEST_CONNECTED_COMPONENT_REPORT, "w+") as f:
        for key in sorted(connected_components_log):
            components = connected_components_log[key]
            largest = max([len(x) for x in components])
            f.write("%d    %d\n" % (key, largest))


def get_cdf(a_list):
    d = {}
    a_list = sorted(a_list)
    size = len(a_list)
    for i, item in enumerate(a_list):
        d[item] = (i+1)/size

    return d


def log_connection_duration_pdf():
    durations = [c.duration() for c in created_connections]
    cdf_dict = get_cdf(durations)

    with open(CONNECTIONS_DURATION_CDF_REPORT, "w+") as f:
        for i in cdf_dict:
            f.write("%f    %f\n" % (i, cdf_dict[i]))


   # with open(CONNECTIONS_DURATION_PDF_REPORT,"w+") as f:
   #    for d in durations:
   #         f.write("%f    ")




def get_average_largest_connected_component():
    l = []
    for components in connected_components_log.values():
        l.append(max([len(x) for x in components]))
    
    if len(l) == 0:
        return 0

    return sum(l)/len(l)


def get_median_largest_connected_component():
    l = []
    for components in connected_components_log.values():
        l.append(max([len(x) for x in components]))

    return get_median(l)


# format: time    number of components (partitions)
# output: number_of_connected_components_report.txt
def log_number_of_connected_components():
    with open(NUMBER_OF_CONNECTED_COMPONENTS_REPORT, "w+") as f:
        for key in sorted(connected_components_log):
            number_of_components = len(connected_components_log[key])
            f.write("%d    %d\n" % (key, number_of_components))


def get_average_number_of_connected_components():
    l = [len(x) for x in connected_components_log.values()]

    if len(l) == 0:
        return 0

    return sum(l) / len(l)


def get_median_number_of_connected_components():
    l = [len(x) for x in connected_components_log.values()]
    return get_median(l)


# returns the median value of a list
def get_median(l):
    l = sorted(l)
    if len(l) % 2 == 1:
        return l[len(l)//2]
    else:
        return (l[len(l)//2] + l[(len(l)//2)-1])/2


def main():
    _init()
    run()

if __name__ == "__main__":
    main()
