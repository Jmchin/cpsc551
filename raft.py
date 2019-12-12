#!/usr/bin/env python3

import random
import sys
import threading
import zmq


class Server:
    """The default server in a Raft cluster

    Can be in one of three states at any given time, depending on
    certain conditions of internal state and of the larger raft
    cluster.

    When first initialized, nodes start off in the Follower state, and
    spawn a thread for handling a randomized election timer. If the
    Follower node does not receive a heartbeat response before the
    thread's timer expires, then the node will transistion into the
    Candidate state and solicit it's peers for votes. If the node
    receives a majority of affirmative votes from its peers, then it
    is promoted to Leader and begins sending its own heartbeat.

    ----------------------------------------------------------------------

    Persistent state on all servers:

    current_term : latest TERM server has seen (initialized to 0,
    increases monotonically

    voted_for : candidate_id that received VOTE in current term, or None

    log[] : the log entries, each entry contains a COMMAND for the
    state machine, as well as the term when received by the leader
    (index starts at 1)

    ----------------------------------------------------------------------

    Volatile state on all servers:

    commit_idx : index of the highest log entry known to be committed
    (initialized to 0, increases monotonically)

    last_applied : index of highest log entry applied to state machine
    (initialized to 0, increases monotonically)

    ----------------------------------------------------------------------

    Volatile state on leaders:

    next_idx[] : for each server in the cluster, store the index of
    the next log entry to send to that particular server (initialized
    to leader last log index + 1)

    match_idx[] : for each server in the cluster, index of highest log
    entry known to be replicated on server (initialized to 0,
    increases monotonically)

    """

    def __init__(self, addr, peers):
        self.addr = addr  # 127.0.0.1:5555
        self.peers = peers
        self.state = "follower"

        # Persistent state on ALL servers
        # ----------------------------------------------------------------------
        self.term = 0
        self.voted_for = None
        self.log = []

        # Volatile state on ALL servers
        # ----------------------------------------------------------------------
        self.commit_idx = 0
        self.last_applied = 0

        self.vote_count = 0
        self.majority = ((len(peers) + 1) // 2) + 1
        self.timeout_thread = None
        self.election_time = 0

        # TRANSPORT
        # ----------------------------------------------------------------------
        self.ctx = zmq.Context()
        self.rep_sock = self.ctx.socket(zmq.REP)  # incoming

        # Setup our REP socket to receive incoming requests
        self.rep_sock.bind(self.addr)

        # LEADER STATE
        # ----------------------------------------------------------------------
        self.next_idxs = None
        self.match_idxs = None

        # bind the response socket to all known peers
        for peer in self.peers:
            self.rep_sock.bind(peer)

        self.follower_loop()

    def randomize_timeout(self):
        """ Sets server's election time to a random value in [150, 300]
        milliseconds

        """
        # self.election_time = random.randrange(150, 300) / 1000
        self.election_time = random.randrange(150, 300) / 100

    def initialize_election_timer(self):
        """ Spawns an election timer thread, with a randomized timeout

        """
        print('Initializing election timer')

        # timer has not expired yet, so reinitialize it
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread.cancel()

        # timeout is randomized upon each initialization
        self.randomize_timeout()

        # spawn a new timeout thread with a new randomized timeout
        self.timeout_thread = threading.Timer(self.election_time,
                                              self.handle_election_timeout)

        self.timeout_thread.start()

    def handle_election_timeout(self):
        """The target function of an election timer thread expiring

        When an election timer expires, the server whose timer expired
        must transition into the Candidate state and begin an election
        by requesting votes from its peer group.

        TODO:

        If election timeout elapses without receiving AppendEntries
        RPC from current leader OR granting vote to candidate: convert
        to candidate

        """

        if self.state != "leader" and not self.voted_for:
            self.state = "candidate"
            self.term += 1
            self.vote_count = 0
            self.initialize_election_timer()
            self.request_votes()

    def request_votes(self):
        """ Request votes from every node in the current cluster

        """
        def request_vote(peer, term):
            # construct a message to send to the peer
            message = {
                "type": "RequestVotes",
                "addr": self.addr,
                "term": self.term
                }
            print(message)
            while self.state == "candidate" and self.term == term:
                # connect to the peer
                sock = self.ctx.socket(zmq.REQ)
                print(f'connecting to peer {peer}')
                sock.connect(peer)
                sock.send_json(message)

                reply = sock.recv()
                if reply:
                    self.heartbeat_reply_handler()
                print(reply)

        # start a thread of control for each peer in the group
        for peer in self.peers:
            threading.Thread(target=request_vote,
                             args=(peer, self.term)).start()

    def follower_loop(self):
        # listen for incoming requests from the leader, or timeout
        while self.state == "follower":
            self.initialize_election_timer()
            while self.timeout_thread.is_alive():
                req = self.rep_sock.recv_json()
                if req["type"] == "RequestVotes":
                    self.reply_vote(req)

    def reply_vote(self, req):
        print(f'RequestVotes from {req["addr"]} with term {req["term"]}')

    # def send_heartbeat(self, follower):
    #     # check if the new follower have same commit index, else we
    #     # tell them to update to our log level if self.log:
    #     # self.update_follower_commitIdx(follower)

    #     message = {"term": self.term, "addr": self.addr}
    #     while self.state == "leader":
    #         start = time.time()
    #         # reply = utils.send(follower, route, message)
    #         # if reply:
    #         #     pass
    #             # self.heartbeat_reply_handler(reply.json()["term"],
    #                                         # reply.json()["commitIdx"])
    #         delta = time.time() - start
    #         # keep the heartbeat constant even if the network speed is varying
    #         print("heartbeating.......")
    #         time.sleep((300 - delta) / 1000)


if __name__ == "__main__":
    # python server.py index ip_list
    if len(sys.argv) == 3:
        index = int(sys.argv[1])
        ip_list_file = sys.argv[2]
        ip_list = []
        # open ip list file and parse all the ips
        with open(ip_list_file) as f:
            for ip in f:
                ip_list.append(ip.strip())
        my_ip = ip_list.pop(index)
        print(f'my_ip: {my_ip}')

        http, host, port = my_ip.split(':')
        # initialize node with ip list and its own ip
        s = Server(my_ip, ip_list)
    else:
        print("usage: python raft.py <index> <ip_list_file>")

# if __name__ == "__main__":
#     print("START")
#     args = sys.argv[1:]
#     print(f"Starting raft server ({sys.argv[1]})")
#     s = Server(sys.argv[1], sys.argv[2])
