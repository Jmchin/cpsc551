# raft.py

# the beginning of a python implementation of the Raft Consensus Algorithm

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

import random
import threading    # make heartbeat RPC in parallel
import zmq          # for our transport


FOLLOWER = 0
CANDIDATE = 1
LEADER = 2

# TODO:

# First, lets start by making sure that nodes start off in the
# Follower state, and after a timeout, transitions to the Candidate
# state and initiates an election


class cfg():
    """Some global values"""
    # in ms
    LOW_TIMEOUT = 150
    HIGH_TIMEOUT = 300

    REQUESTS_TIMEOUT = 50
    HB_TIME = 50
    MAX_LOG_WAIT = 50


def random_timeout():
    """Returns a randomized timeout value"""
    return random.randrange(cfg.LOW_TIMEOUT, cfg.HIGH_TIMEOUT) / 1000


class Server:
    def __init__(self, addr, cluster_members):
        self.addr = addr
        self.cluster = set(cluster_members)
        self.state = FOLLOWER
        self.current_term = 0
        self.log = []
        self.majority = ((len(self.cluster) + 1) // 2) + 1

        # volatile state on all servers
        self.commit_idx = 0    # index of highest log entry known to be committed
        self.last_applied = 0  # index of highest log entry applied to state machine

        # volatile state on leaders
        self.next_index = []   # index of next log entry to send
        self.match_index = []  # index of highest replicated entry

    def init_timeout(self):
        """ Initialize a timeout thread

        """
        self.reset_timeout()
        # safety guarantee, timeout thread may expire after election
        if self.timeout_thread and self.timeout_thread.isAlive():
            return
        self.timeout_thread = threading.Thread(target=self.timeout_loop)
        self.timeout_thread.start()

    def start_election():
        """ Start a raft election

        After election timer expires, we need to elect a new leader. The
        first node whose election timer expires will invoke this method,
        change its state from FOLLOWER to CANDIDATE, and request votes
        from all other servers in the Raft cluster.

        When an election is started, the server initiating the
        election must increment their current term, vote for
        themselves, and then await

        """
        pass


class State:
    def __init__(self):
        # persistent state: update on stable storage before responding
        # to RPC
        self.currentTerm = 0
        self.votedFor = None
        self.log = []   # list of log entries, each entry contains
        # command and term when received by leader
        # (first index is 1)

        # volatile state
        self.commitIndex = 0
        self.lastApplied = 0

        # state for leaders (reiniatilize after election)
        self.nextIndex = []       # index of the next log entry to
        # send to server (init to
        # leader.log[len(leaderlog)-1]

        self.matchIndex = []      # index of highest log entry known to
        # be replicated on server (init to 0,
        # increase monotonically)


class AppendEntries:
    """Invoked by leader to replicate log entries, also used as heartbeat

    """

    # TODO: Should this be a method invoked by the leader node, instead of a class?
    def __init__(self, term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit):
        self.term = term
        self.leaderId = leaderId
        self.prevLogIndex = prevLogIndex
        self.prevLogTerm = prevLogTerm
        self.entries = entries
        self.leaderCommit = leaderCommit


class RequestVote:
    """ Invoked by candidates to gather votes

    """

    # TODO: Should this be a method invoked by candidate nodes, instead of a class?
    def __init__(self, term, candidateId, lastLogIndex, lastLogTerm):
        self.term = term
        self.candidateId = candidateId
        self.lastLogIndex = lastLogIndex
        self.lastLogTerm = lastLogTerm
