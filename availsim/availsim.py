#!/usr/bin/env python

from __future__ import generators
import sys

from utils import str2chordID, size_rounder
import dhash

def get_node_id (args):
    try:
	return long(args)
    except:
	try:
	    return str2chordID (args)
	except:
	    raise SyntaxError, "Bad ID specification"
        
class event:
    def ev_getnode (my, args):
        id = get_node_id (args[0])
        my.id = id

    def ev_getblock (my, args):
        my.id = get_node_id (args[0])
        try:
            id = long (args[1])
        except:
            id = str2chordID (args[1])
        my.block = id
        # size is optional
        try:
            my.size = int(args[2])
        except:
            my.size = 8192
    
    def __init__ (my, time, type, *args):
        my.time = time
        my.type = type
                
        etypes = {
            'join'  : my.ev_getnode,
            'fail'  : my.ev_getnode,
            'crash' : my.ev_getnode,
            'insert': my.ev_getblock
        }
        if type not in etypes:
            raise TypeError, "Unknown event type"
	apply (etypes[type], args)
        
    def __str__ (my):
        return "%ld %s" % (time, type)

class simulator:
    def __init__ (my, dht):
        my.dh = dht
        
    def run (my, evgen, monitor, monint):
        last_time = 0
	do_monitor = 0
	next_monitor_time = monint
        for ev in evgen:
            assert last_time <= ev.time, "Woah! Time can't go backwards %d > %d." % (last_time, ev.time)
            if last_time != ev.time:
		# Notify DHash of time change
                my.dh.time_changed (last_time, ev.time)
		# And call monitor periodically
		if last_time > next_monitor_time or do_monitor:
		    monitor (last_time, my.dh)
		    next_monitor_time += monint
		    # We expect a lot to happen in an hour...
		do_monitor = 0

            if ev.type == "join":
                my.dh.add_node (ev.id)
		do_monitor = 1
            if ev.type == "fail":
                my.dh.fail_node (ev.id)
		do_monitor = 1
            if ev.type == "crash":
                my.dh.crash_node (ev.id)
		do_monitor = 1
            if ev.type == "insert":
                my.dh.insert_block (ev.id, ev.block, ev.size)
            last_time = ev.time
        monitor (last_time + 1, my.dh)

def file_evgen (fname):
    lineno = 0
    fh = open (fname)
    for l in fh:
        lineno += 1
        # Rudimentary comment parsing
        if l[0] == '#': continue
        a = l.strip ().split ()
        try:
            ev = event (int(a[0]), a[1].lower (), a[2:])
            yield ev
        except Exception, e:
            sys.stderr.write ("Bad event at line %d: %s\n" % (lineno, e))

sbkeys = ['insert', 'join_repair_write', 'join_repair_read',
	  'failure_repair_write', 'failure_repair_read']
def _monitor (t, dh):
    stats = {}
    allnodes = dh.allnodes.values ()

    stats['usable_bytes'] = sum (dh.blocks.values ())
    stats['sent_bytes']   = sum ([n.sent_bytes for n in allnodes])
    stats['disk_bytes']   = sum ([n.bytes      for n in allnodes])
    stats['avail_bytes']  = sum ([n.bytes      for n in dh.nodes])

    for k in sbkeys:
	stats['sent_bytes::%s' % k] = \
		sum ([n.sent_bytes_breakdown.get (k, 0) for n in allnodes])

    blocks = {}
    for n in dh.nodes:
	for b in n.blocks:
	    blocks[b] = blocks.get (b, 0) + 1
    extant = blocks.values ()
    try: 
	avg = sum (extant, 0.0) / len (extant)
	minimum = min (extant)
	maximum = max (extant)
    except:
	avg, minimum, maximum = 0, 0, 0
    stats['extant_avg'] = avg
    stats['extant_min'] = minimum
    stats['extant_max'] = maximum

    return stats

def print_monitor (t, dh):
    s = _monitor (t, dh)

    print "%4d" % t, "%4d nodes;" % len(dh.nodes), 
    print "%sB sent;" % size_rounder (s['sent_bytes']),
    print "%sB put;" % size_rounder (s['usable_bytes']),
    print "%sB avail;" % size_rounder (s['avail_bytes']),
    print "%sB stored;" % size_rounder (s['disk_bytes']),
    print "%d/%5.2f/%d extant;" % s['extant_min', 'extant_avg', 'extant_max'],
    print "%d/%d blocks avail" % (dh.available_blocks (), len (dh.blocks)),
    for k in sbkeys:
	print "%sB sent[%s];" % (size_rounder(s['sent_bytes::%s' % k]), k)

def parsable_monitor (t, dh):
    s = _monitor (t, dh)

    print t, len(dh.nodes), 
    print ' '.join(["%d" % s[k] for k in ['sent_bytes','usable_bytes','avail_bytes','disk_bytes']]),
    print s['extant_min'], "%5.2f" % s['extant_avg'], s['extant_max'],
    print dh.available_blocks (), len (dh.blocks),
    for k in sbkeys:
	print "%d" % s['sent_bytes::%s' % k],
    print

if __name__ == '__main__':
    import sys
    import getopt

    def usage ():
	sys.stderr.write ("%s events.txt dhash_fragments 7 14\n" % sys.argv[0])

    # default monitor
    monitor = print_monitor
    monint  = 60
    try:
	opts, cmdv = getopt.getopt (sys.argv[1:], "ms:")
    except getopt.GetoptError:
        usage ()
        sys.exit (1)
    for o, a in opts:
        if o == '-m':
            monitor = parsable_monitor
	elif o == '-s':
	    monint = int (a)
            
    if len(cmdv) < 2:
        usage ()
	sys.exit (1)

    evfile = cmdv[0]
    dtype  = cmdv[1]
    gdh = None
    if (dtype == "fragments"):
	try:
	    dfrags = int (cmdv[2])
	except:
	    dfrags = 3
	try:
	    efrags = int (cmdv[3])
	except:
	    efrags = 2 * dfrags
	gdh = dhash.dhash_fragments (dfrags, efrags)
    elif (dtype == "replica"):
	try:
	    replicas = int (cmdv[2])
	except:
	    replicas = 3
	gdh = dhash.dhash_replica (replicas)
    elif (dtype == "replica_norepair"):
	try:
	    replicas = int (cmdv[2])
	except:
	    replicas = 3
	gdh = dhash.dhash_replica_norepair (replicas)
    else:
	sys.stderr.write ("invalid dhash type\n")
        usage ()
	sys.exit (1)

    sim = simulator (gdh)
    eg = file_evgen (evfile)
    sim.run (eg, monitor, monint)
    