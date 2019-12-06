# raft.py

# the beginning of a python implementation of the Raft Consensus Algorithm

import threading    # make heartbeat RPC in parallel


FOLLOWER = 0
CANDIDATE = 1
LEADER = 2


# Each server in our cluster, which needs to maintain a replicated
# state machine consistent between them

class Server:
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
    def __init__(self, addr, cluster_members):
        self.addr = addr
        self.cluster = cluster_members
        self.state = FOLLOWER
        self.current_term = 0
        self.log = []
        self.majority = ((len(self.cluster) + 1) // 2) + 1

        # volatile state on all servers
        self.commit_idx = 0    # index of highest log entry known to be committed
        self.last_applied = 0  # index of highest log entry applied to state machine

        # volatile state on leaders
        self.next_index = []   # for each server, index of next log entry to send
        self.match_index = []  # for each server, index of highest
                               # entry known to be replicated


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
