# -*- coding: utf-8 -*-
"""
test_celllab_cts.py: Unit-test function for CellLabCTS.

Created on Thu Jul  9 08:20:06 2015

@author: gtucker
"""

from nose.tools import assert_equal
from numpy.testing import assert_array_equal
from landlab import RasterModelGrid, HexModelGrid
from landlab.ca.celllab_cts import Transition, Event
from landlab.ca.raster_cts import RasterCTS
from landlab.ca.oriented_raster_cts import OrientedRasterCTS
from landlab.ca.hex_cts import HexCTS
from landlab.ca.oriented_hex_cts import OrientedHexCTS
from heapq import heappush
from heapq import heappop
import numpy as np

# For dev
from landlab.ca.celllab_cts import _RUN_NEW


def callback_function(ca, node1, node2, time_now):
    """
    This function is passed as an argument to a transition event, and then
    called automatically by CellLabCTSModel's do_event() method.
    """
    pass
#    elapsed_time = time_now - ca.last_update_time[node1]
#    if ca.node_state[node1]==1:
#        ca.prop_data[ca.propid[node1]]+=100*elapsed_time
#    elapsed_time = time_now - ca.last_update_time[node2]
#    if ca.node_state[node2]==1:
#        ca.prop_data[ca.propid[node2]]+=100*elapsed_time
#



def test_transition():
    """Test instantiation of Transition() object."""
    t = Transition((0, 0, 0), (1, 1, 0), 1.0, name='test',
                   swap_properties=False, prop_update_fn=None)
    assert_equal(t.from_state, (0,0,0))
    assert_equal(t.to_state, (1,1,0))
    assert_equal(t.rate, 1.0)
    assert_equal(t.name, 'test')
    assert_equal(t.swap_properties, False)
    assert_equal(t.prop_update_fn, None)


def test_event_init():
    """Test instantiation of Event() object"""
    e = Event(2.0, 3, 4, propswap=False, prop_update_fn=None)
    assert_equal(e.time, 2.0)
    assert_equal(e.link, 3)
    assert_equal(e.xn_to, 4)
    assert_equal(e.propswap, False)
    assert_equal(e.prop_update_fn, None)


def test_event_lt():
    """Test Event.__lt__()"""
    e1 = Event(2.0, 3, 4)
    e2 = Event(5.0, 2, 3)
    assert_equal(e1<e2, True)


def test_raster_cts():
    """
    Tests instantiation of a RasterCTS and implementation of one transition,
    with a callback function.
    """

    # Set up a small grid with no events scheduled
    mg = RasterModelGrid(4, 4, 1.0)
    mg.set_closed_boundaries_at_grid_edges(True, True, True, True)
    node_state_grid = mg.add_ones('node', 'node_state_map', dtype=int)
    node_state_grid[6] = 0
    ns_dict = { 0 : 'black', 1 : 'white' }
    xn_list = []
    xn_list.append( Transition((1,0,0), (0,1,0), 0.1, '', True, callback_function))
    pd = mg.add_zeros('node', 'property_data', dtype=int)
    pd[5] = 50
    ca = RasterCTS(mg, ns_dict, xn_list, node_state_grid, prop_data=pd,
                   prop_reset_value=0)

    # Test the data structures
    assert (ca.num_link_states==4), 'wrong number of link states'
    assert (ca.prop_data[5]==50), 'error in property data'
    assert (ca.num_node_states==2), 'error in num_node_states'
    assert (ca.link_orientation[-1]==0), 'error in link orientation array'
    assert (ca.link_state_dict[(1, 0, 0)]==2), 'error in link state dict'
    assert (ca.n_xn[2]==1), 'error in n_xn'
    assert (ca.node_pair[1]==(0, 1, 0)), 'error in cell_pair list'

    if _RUN_NEW:
        assert (len(ca.priority_queue._queue)==1), 'event queue has wrong size'
        assert (ca.next_trn_id.size==24), 'wrong size next_trn_id'
        assert (ca.trn_id.shape==(4, 1)), 'wrong size for xn_to'
        assert (ca.trn_id[2][0]==0), 'wrong value in xn_to'
        assert (ca.trn_to[0] == 1), 'wrong trn_to state'
        assert (ca.trn_rate[0] == 0.1), 'wrong trn rate'
        assert (ca.trn_propswap[0] == 1), 'wrong trn propswap'
        assert (ca.trn_prop_update_fn == callback_function), 'wrong prop upd'
    else:
        assert (len(ca.event_queue)==1), 'event queue has wrong size'
        assert (ca.xn_to.size==4), 'wrong size for xn_to'
        assert (ca.xn_to.shape==(4, 1)), 'wrong size for xn_to'
        assert (ca.xn_to[2][0]==1), 'wrong value in xn_to'
        assert (ca.xn_rate[2][0]==0.1), 'error in transition rate array'

    # Manipulate the data in the event queue for testing:

    if _RUN_NEW:
        # pop the scheduled event off the queue
        (event_time, index, event_link) = ca.priority_queue.pop()        
        assert (ca.priority_queue._queue==[]), \
                                'event queue should now be empty but is not'

        # engineer an event
        ca.priority_queue.push(8, 1.0)
        ca.next_update[8] = 1.0
        ca.next_trn_id[8] = 0

    else:
        # pop the scheduled event off the queue
        ev = heappop(ca.event_queue)
        assert (ca.event_queue==[]), 'event queue should now be empty but is not'
    
        # engineer an event
        ev.time = 1.0
        ev.link = 8
        ev.xn_to = 1
        ev.propswap = True
        ev.prop_update_fn = callback_function
        ca.next_update[8] = 1.0
    
        # push it onto the event queue
        heappush(ca.event_queue, ev)

    # run the CA
    ca.run(2.0)

    # some more tests.
    # Is current time advancing correctly? (should only go to 1.0, not 2.0)
    # Did the two nodes (5 and 6) correctly exchange states?
    # Did the property ID and data arrays get updated? Note that the "propswap"
    # should switch propids between nodes 5 and 6, and the callback function
    # should increase the value of prop_data in the "swap" node from 50 to 150.
    assert (ca.current_time==1.0), 'current time incorrect'
    assert (ca.node_state[5]==0), 'error in node state 5'
    assert (ca.node_state[6]==1), 'error in node state 6'
    #assert (ca.prop_data[ca.propid[6]]==150), 'error in prop swap'


def test_oriented_raster_cts():
    """Tests instantiation of an OrientedRasterCTS() object"""
    mg = RasterModelGrid(3, 3, 1.0)
    nsd = {0 : 'oui', 1 : 'non'}
    xnlist = []
    xnlist.append(Transition((0,1,0), (1,1,0), 1.0, 'hopping'))
    nsg = mg.add_zeros('node', 'node_state_grid')
    orcts = OrientedRasterCTS(mg, nsd, xnlist, nsg)

    assert_equal(orcts.num_link_states, 8)
    #assert_array_equal(orcts.link_orientation, [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    assert_array_equal(orcts.link_orientation, [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0])


def test_hex_cts():
    """Tests instantiation of a HexCTS() object"""
    mg = HexModelGrid(3, 2, 1.0, orientation='vertical', reorient_links=True)
    nsd = {0 : 'zero', 1 : 'one'}
    xnlist = []
    xnlist.append(Transition((0,1,0), (1,1,0), 1.0, 'transitioning'))
    nsg = mg.add_zeros('node', 'node_state_grid')
    hcts = HexCTS(mg, nsd, xnlist, nsg)

    assert_equal(hcts.num_link_states, 4)
    assert_array_equal(hcts.link_orientation, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])


def test_oriented_hex_cts():
    """Tests instantiation of an OrientedHexCTS() object"""
    mg = HexModelGrid(3, 2, 1.0, orientation='vertical', reorient_links=True)
    nsd = {0 : 'zero', 1 : 'one'}
    xnlist = []
    xnlist.append(Transition((0,1,0), (1,1,0), 1.0, 'transitioning'))
    nsg = mg.add_zeros('node', 'node_state_grid')
    ohcts = OrientedHexCTS(mg, nsd, xnlist, nsg)
    
    assert_equal(ohcts.num_link_states, 12)
    #assert_array_equal(ohcts.link_orientation, [2, 1, 0, 0, 0, 2, 1, 0, 2, 1, 0])
    assert_array_equal(ohcts.link_orientation, [2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1])
    
    
def test_priority_queue():
    """Test import and use of priority queue."""
    from ..cfuncs import PriorityQueue
    
    # Create a priority queue
    pq = PriorityQueue()
    
    # push a bunch of events
    pq.push(2, 2.2)
    pq.push(5, 5.5)
    pq.push(0, 0.11)
    pq.push(4, 4.4)
    pq.push(1, 1.1)
    pq.push(3, 3.3)

    # pop a bunch of events
    (priority, index, item) = pq.pop()
    assert (priority == 0.11), 'incorrect priority in PQ test'
    assert (index == 2), 'incorrect index in PQ test'
    assert (item == 0), 'incorrect item in PQ test'

    (priority, index, item) = pq.pop()
    assert (priority == 1.1), 'incorrect priority in PQ test'
    assert (index == 4), 'incorrect index in PQ test'
    assert (item == 1), 'incorrect item in PQ test'

    (priority, index, item) = pq.pop()
    assert (priority == 2.2), 'incorrect priority in PQ test'
    assert (index == 0), 'incorrect index in PQ test'
    assert (item == 2), 'incorrect item in PQ test'

    (priority, index, item) = pq.pop()
    assert (priority == 3.3), 'incorrect priority in PQ test'
    assert (index == 5), 'incorrect index in PQ test'
    assert (item == 3), 'incorrect item in PQ test'

    (priority, index, item) = pq.pop()
    assert (priority == 4.4), 'incorrect priority in PQ test'
    assert (index == 3), 'incorrect index in PQ test'
    assert (item == 4), 'incorrect item in PQ test'

    (priority, index, item) = pq.pop()
    assert (priority == 5.5), 'incorrect priority in PQ test'
    assert (index == 1), 'incorrect index in PQ test'
    assert (item == 5), 'incorrect item in PQ test'

def test_run_oriented_raster():
    """Test running with a small grid, 2 states, 4 transition types."""

    # Create an OrientedRaster with a 3x5 raster grid. Test model has 2 node
    # states and 4 transition types.
    grid = RasterModelGrid((3, 5))
    nsd = {0 : 'zero', 1 : 'one'}
    trn_list = []
    trn_list.append(Transition((0, 1, 0), (1, 0, 0), 1.0))
    trn_list.append(Transition((1, 0, 0), (0, 1, 0), 2.0))
    trn_list.append(Transition((0, 1, 1), (1, 0, 1), 3.0))
    trn_list.append(Transition((0, 1, 1), (1, 1, 1), 4.0))
    ins = np.arange(15) % 2  # makes a checkerboard pattern
    cts = OrientedRasterCTS(grid, nsd, trn_list, ins)

    # Run to 1st transition, at ~0.12
    cts.run(0.15)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0])

    # Run to 2nd transition, at ~0.19
    cts.run(0.2)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0])

    # Run to 3rd transition, at ~0.265
    cts.run(0.27)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0])

    # Run to 4th transition, at ~0.276 (transition is ignored)
    cts.run(0.28)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0])

    # Run to 5th transition, at ~0.461 (ignored)
    cts.run(0.5)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0])

    # Run to 6th transition, at ~0.648
    cts.run(0.65)
    assert_array_equal(cts.node_state,
                       [0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0])


def test_grain_hill_model():
    """Run a lattice-grain-based hillslope evolution model."""
    import grain_hill_as_class
    from grain_hill_as_class import GrainHill

    params = grain_hill_as_class.get_params_from_input_file('grain_hill_params.txt')
    grid_size = (int(params['number_of_node_rows']), 
                 int(params['number_of_node_columns']))
    grain_hill_model = GrainHill(grid_size, **params)
    grain_hill_model.run()
    
    # Now test
    assert_array_equal(grain_hill_model.grid.at_node['node_state'][:18],
                       [8, 7, 7, 7, 7, 7, 7, 7, 7, 8, 0, 7, 7, 7, 7, 0, 7, 7])

    # Try with an uplift step
    params['uplift_interval'] = 5.0
    params['run_duration'] = 15.0
    grain_hill_model = GrainHill(grid_size, **params)
    grain_hill_model.run()

    # Test
    assert_array_equal(grain_hill_model.grid.at_node['node_state'][20:38],
                       [0, 7, 7, 7, 7, 0, 7, 7, 7, 0, 0, 0, 7, 7, 0, 0, 0, 7])


if __name__ == '__main__':
    test_grain_hill_model()
    test_transition()
    test_raster_cts()
    test_oriented_raster_cts()
    test_hex_cts()
    test_oriented_hex_cts()
    test_run_oriented_raster()