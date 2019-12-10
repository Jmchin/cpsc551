# raft.py

# the beginning of a python implementation of the Raft Consensus Algorithm


# Raft Consensus:

# Raft is a consensus algorithm for managing a replicated log. The
# original authors, Ongaro and Ousterhout have developed the Raft
# algorithm, breaking the consensus problem into 3 mostly independent
# subproblems. We are going to implement Raft by using this architecture.

# NOTES
# ----------------------------------------------------------------------

# Each server in our cluster, which needs to maintain a replicated
# state machine consistent between them

# Need to connect each of these Raft servers to a
# tuplespace/adapter pair. The tuplespace will be our replicated
# state machine that we will maintain consistently between however
# many servers are in our cluster

# Need to maintain a log of Entries. Entries are operations that
# need to be sequenced by the Leader server, and can be marked as
# committed or not. Once a majority of servers have received the
# event to be committed, the leader commits the operation to the
# log, at a specified index, applies the operation to its state
# machine, and returns the results to the calling client

# Clients need to connect to the Servers in our Raft cluster
# transparently. The client should not need to know about the
# underlying structure of the Raft cluster (i.e Leader and
# Followers). A client connects to one of the servers in the
# cluster and requests a system change. The server, if a follower,
# will forward the request directly to the leader server for the
# current term.

# Each server needs to keep track of its current term, initialized
# to 0, increasing monotonically with each new election

# Each server needs to know how many other servers are in the
# cluster to calculate the majority threshold, for determining
# elections and for the distributed commit

# ----------------------------------------------------------------------


# TODO:
# ----------------------------------------------------------------------

# Finish the election algorithm:

# Right now our election algorithm is capable of electing a leader in
# a single node architecture. This is simply a proof-of-concept at
# this stage. Next step we need to scale up to a cluster size of N >=
# 3, preferably N = 5, and test the election protocol


# Implement Leader Heartbeat:

# The leader's heartbeat is a period AppendEntries RPC into all of the
# Follower servers in the cluster

# ----------------------------------------------------------------------

from enum import Enum

import random
import time
import threading    # make heartbeat RPC in parallel
import zmq          # our transport layer


class State(Enum):
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2


def random_timeout():
    return random.randrange(150, 300) / 1000


# TODO
class Vote:
    """ A vote for a leader election

    """
    pass


# TODO
class LogEntry:
    """ An entry in our replicated, distributed log

    LogEntries include the current term number and the command to be
    replicated to the StateMachine

    """
    pass


# TODO
class Log:
    """ The replicated, distributed log

    """
    pass


# TODO
class Snapshot:
    """ A complete system state for a range of log entries

    Used in Log Compaction to save space preventing unbounded log growth.

    """
    pass


# TODO
class StateMachine:
    """ The state machine that we want to replicate across the cluster

    For our purposes, this will be a Rinda tuplespace with an attached adapter
    """


# TODO
class Server:
    """The basic unit of our Raft Server Cluster.

    Each server can be in one of three states:

    1) Follower
    2) Candidate
    3) Leader

    The Raft Consensus Algorithm models the servers in the cluster
    with a master/slave relationship, where at any given time, there
    is exactly one leader whose log is the source of truth for the
    entire cluster. In the event that there are more than one leader
    in the cluster, both will step down, and a new election will begin
    upon the next election timeout.

    The leader of the cluster will periodically send AppendEntry RPCs
    to all of its followers. This serves as the leader's heartbeat.

    """
    def __init__(self, addr, cluster):
        # Probably need a zmq context here for our transport
        self.addr = addr
        self.cluster = cluster
        self.state = State.FOLLOWER
        self.current_term = 0
        self.votes = set()  # holds a set of cluster members that have
                            # voted for this node

        # TODO: this should be the tuplespace
        self.state_machine = None
        self.log = []
        self.majority = ((len(self.cluster) + 1) // 2) + 1

        # volatile state on all servers
        self.commit_idx = 0    # index of highest log entry known to be committed
        self.last_applied = 0  # index of highest log entry applied to state machine

        # volatile state on leaders
        # TODO, reinitalize these after Election
        self.next_idx = []   # for each server, index of next log entry to send
        self.match_idx = []  # for each server, index of highest entry
                             # known to be replicated

        self.timeout_thread = None



    # TIMEOUT
    # ----------------------------------------------------------------------
    def reset_election_timeout(self):
        """ Returns some random amount of time after the current time

        """
        self.election_time = time.time() + random_timeout()


    def init_timeout(self):
         """ Initialize a thread for handling election timeouts

         """
         self.reset_election_timeout()

         if self.timeout_thread and self.timeout_thread.is_alive():
             return
         self.timeout_thread = threading.Thread(target=self.handle_timeout)
         self.timeout_thread.start()


    def handle_timeout(self):
        """ The timeout thread handler

        """
        while self.state != State.LEADER:
            # see if our time expired
            d = self.election_time - time.time()
            self.start_election() if d < 0 else time.sleep(d)


    # ELECTION
    # ----------------------------------------------------------------------


    def request_vote(self, vote_for):
        """ Request votes for the current election Term

        """
        self.votes.add(vote_for)
        if len(self.votes) >= self.majority:
            # become the leader
            self.state = State.LEADER
            # log the result
            print(f'LEADER {self.addr} {self.current_term}')
            # announce your leadership and term
            self.heartbeat()


    def start_election(self):
        """ Start an election because we timed out

        """
        self.current_term += 1
        self.state = State.CANDIDATE
        self.init_timeout()        # timeout before restarting election
        self.request_vote(self.addr)


    # TODO
    def heartbeat(self):
        """ Empty AppendEntries RPC sent to each Follower

        For now, lets send this using REQ-REP ZMQ sockets
        """
        pass


    # TODO
    def install_snapshot(self, term, leaderId, lastIncludedIndex,
                         lastIncludedTermOffset, data, done):
        """ Install the most recent snapshot to server

        """
        pass


# class State:
#     def __init__(self):
#         # persistent state: update on stable storage before responding
#         # to RPC
#         self.currentTerm = 0
#         self.votedFor = None
#         self.log = []   # list of log entries, each entry contains
#                         # command and term when received by leader
#                         # (first index is 1)

#         # volatile state
#         self.commitIndex = 0
#         self.lastApplied = 0

#         # state for leaders (reiniatilize after election)
#         self.nextIndex = []       # index of the next log entry to
#                                   # send to server (init to
#                                   # leader.log[len(leaderlog)-1]

#         self.matchIndex = []      # index of highest log entry known to
#                                   # be replicated on server (init to 0,
#                                   # increase monotonically)


# class AppendEntries:
#     """Invoked by leader to replicate log entries, also used as heartbeat

#     """

#     # TODO: Should this be a method invoked by the leader node, instead of a class?
#     def __init__(self, term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit):
#         self.term = term
#         self.leaderId = leaderId
#         self.prevLogIndex = prevLogIndex
#         self.prevLogTerm = prevLogTerm
#         self.entries = entries
#         self.leaderCommit = leaderCommit


# class RequestVote:
#     """ Invoked by candidates to gather votes

#     """

#     # TODO: Should this be a method invoked by candidate nodes, instead of a class?
#     def __init__(self, term, candidateId, lastLogIndex, lastLogTerm):
#         self.term = term
#         self.candidateId = candidateId
#         self.lastLogIndex = lastLogIndex
#         self.lastLogTerm = lastLogTerm
