from xain.grpc import coordinator_pb2
from xain.grpc.participant import ParState, StateRecord, transit


def test_from_start():
    st = StateRecord()
    assert st.lookup() == (ParState.WAITING_FOR_SELECTION, 0)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.ROUND)
    transit(st, hb)
    assert st.lookup() == (ParState.TRAINING, 0)
    # should return immediately
    assert st.wait_until_selected_or_done() == ParState.TRAINING


def test_waiting_to_training_i():
    st = StateRecord(state=ParState.WAITING_FOR_SELECTION)
    i = 5
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.ROUND, round=i)
    transit(st, hb)
    assert st.lookup() == (ParState.TRAINING, i)
    # should return immediately
    assert st.wait_until_selected_or_done() == ParState.TRAINING


def test_waiting_to_done():
    st = StateRecord(state=ParState.WAITING_FOR_SELECTION, round=2)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.FINISHED)
    transit(st, hb)
    assert st.lookup() == (ParState.DONE, 2)
    # should return immediately
    assert st.wait_until_selected_or_done() == ParState.DONE


def test_waiting_to_waiting():
    st = StateRecord(state=ParState.WAITING_FOR_SELECTION, round=3)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.STANDBY)
    transit(st, hb)
    assert st.lookup() == (ParState.WAITING_FOR_SELECTION, 3)


def test_training_to_training():
    st = StateRecord(state=ParState.TRAINING, round=4)
    start_state = st.lookup()
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.STANDBY)
    transit(st, hb)
    assert st.lookup() == start_state
    hb.state = coordinator_pb2.ROUND
    transit(st, hb)
    assert st.lookup() == start_state
    hb.state = coordinator_pb2.FINISHED
    transit(st, hb)
    assert st.lookup() == start_state


def test_posttraining_to_training():
    st = StateRecord(state=ParState.POST_TRAINING, round=5)
    start_state = st.lookup()
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.ROUND, round=5)
    transit(st, hb)
    assert st.lookup() == start_state
    # old round? shouldn't affect me...
    hb.round = 0
    transit(st, hb)
    assert st.lookup() == start_state
    # NOTE a "future" round e.g. 7 would be unexpected under current assumptions
    # it should be preceded by a STANDBY to indicate nonselection for round 6

    # selected for next round
    hb.round = 6
    transit(st, hb)
    assert st.lookup() == (ParState.TRAINING, 6)
    # should return immediately
    assert st.wait_until_next_round() == ParState.TRAINING


def test_posttraining_to_done():
    st = StateRecord(state=ParState.POST_TRAINING, round=6)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.FINISHED)
    transit(st, hb)
    assert st.lookup() == (ParState.DONE, 6)


def test_posttraining_to_waiting():
    st = StateRecord(state=ParState.POST_TRAINING, round=7)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.STANDBY)
    transit(st, hb)
    assert st.lookup() == (ParState.WAITING_FOR_SELECTION, 7)


def test_restart_round():
    # participant has done its training for round 8
    st = StateRecord(state=ParState.POST_TRAINING, round=8)
    hb = coordinator_pb2.HeartbeatReply(state=coordinator_pb2.STANDBY)
    transit(st, hb)
    assert st.lookup() == (ParState.WAITING_FOR_SELECTION, 8)
    hb.state = coordinator_pb2.ROUND
    # but still in round 8! => the round was restarted
    transit(st, hb)
    # re-do the training...
    assert st.lookup() == (ParState.TRAINING, 8)
