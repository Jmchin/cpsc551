#!/usr/bin/env python3

import random
import sys
import time
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
        self.staged = None

        self.vote_count = 0
        self.majority = ((len(peers) + 1) // 2) + 1
        self.timeout_thread = None
        self.election_time = 0

        # TRANSPORT
        # ----------------------------------------------------------------------
        self.ctx = zmq.Context()
        self.rep_sock = self.ctx.socket(zmq.REP)
        self.rep_sock.bind(self.addr)
        self.rep_poll = zmq.Poller()
        self.rep_poll.register(self.rep_sock, zmq.POLLIN)

        # LEADER STATE
        # ----------------------------------------------------------------------
        self.next_idxs = None
        self.match_idxs = None

        # enter follower state
        self.loop()

    # UTILITIES
    # ----------------------------------------------------------------------
    def randomize_timeout(self):
        """ Sets server's election time to a random value in [150, 300]
        milliseconds

        """
        # self.election_time = random.randrange(150, 300) / 1000
        self.election_time = random.randrange(150, 300) / 100

    # ELECTION
    # ----------------------------------------------------------------------
    def initialize_election_timer(self):
        """ Spawns an election timer thread, with a randomized timeout

        """
        print('Initializing election timer')
        # timer has not expired yet, so reinitialize it
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread.cancel()

        self.randomize_timeout()
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
            self.voted_for = self.addr
            self.vote_count = 1
            self.initialize_election_timer()
            self.request_votes()

    def request_votes(self):
        """ Request votes from every node in the current cluster

        Spawns a thread for each peer in the group, and awaits their response.
        """
        def request_vote(peer, term):
            # construct a message to send to the peer
            message = {
                "type": "RequestVotes",
                "addr": self.addr,
                "term": self.term,
                "staged": self.staged,
                "commitIdx": self.commit_idx,
                "threadId": threading.get_ident(),
                "activeCount": threading.active_count()
                }

            print(message)

            # initializes outbound comms socket
            with self.ctx.socket(zmq.REQ) as sock:
                # sock = self.ctx.socket(zmq.REQ)
                sock.setsockopt(zmq.LINGER, 1)
                # connect socket to peer
                sock.connect(peer)
                print(f'connecting to peer: {peer}')

                # TODO: THIS IS BLOCKING US EVEN THOUGH ITS IN A SEPARATE THREAD,
                # HOW DO I FIX THIS SHIT?
                # send our message
                try:
                    sock.send_json(message, flags=zmq.NOBLOCK)
                except Exception as e:
                    sock.close()
                    pass

                # poll this channel for incoming requests (i.e vote responses)
                poll = zmq.Poller()
                poll.register(sock, zmq.POLLIN)

                events = poll.poll(timeout=1000)  # 1 second

                if len(events) > 0:
                    resp = sock.recv_json(flags=zmq.NOBLOCK)
                    requester_term = resp["term"]
                    print(f'REQUESTER_TERM: {requester_term}')
                    if resp["voteGranted"]:
                        self.increment_vote()
                    if requester_term > self.term:
                        print("RECEIVED NEWER TERM: Becoming FOLLOWER")
                        self.term = requester_term
                        self.state = "follower"
                else:
                    print("Timeout processing auth request!")

        for peer in self.peers:
            t = threading.Thread(target=request_vote,
                                 args=(peer, self.term)).start()
            # t = threading.Timer()
            # self.timeout_thread = threading.Timer(self.election_time,
            #                                       self.handle_election_timeout)

    def reply_vote(self, req):
        # from the REP socket, REPLY back to the requesting thread
        message = {
            "type": "RequestVotesResponse",
            "addr": self.addr,
            "term": self.term,
            "voteGranted": False
        }

        # now we need to check whether or not we should grant the vote
        if self.term < req["term"] and self.commit_idx <= req["commitIdx"] and (self.staged == req["staged"]):
            self.initialize_election_timer()
            self.term = req["term"]
            message["voteGranted"] = True
            print(f'VOTING for {req["addr"]} as LEADER for TERM {req["term"]}')

        try:
            self.rep_sock.send_json(message, flags=zmq.NOBLOCK)
        except Exception as e:
            pass

    def increment_vote(self):
        self.vote_count += 1
        if self.vote_count >= self.majority:
            # become the leader
            print(f'{self.addr} becomes LEADER of term {self.term}')
            self.state = "leader"
            self.start_heartbeat()

    def start_heartbeat(self):
        print(f'Starting HEARTBEAT')

        # spawn a thread for each peer for RPCs
        for peer in self.peers:
            t = threading.Thread(target=self.append_entries, args=(peer,))
            t.start()


    # TODO: Upon election, send initial empty AppendEntries
    # heartbeat to each server; repeat during idle periods to
    # prevent election timeout
    def append_entries(self, peer):
        print(f'HEARTBEAT to {peer}')
        while self.state == "leader":
            start = time.time()

    def handle_append_entries(self):
        pass

    # BEHAVIOR
    # ----------------------------------------------------------------------
    def loop(self):
        while True:
            if self.state == "follower":
                self.follower_loop()
            elif self.state == "candidate":
                self.candidate_loop()
            elif self.state == "leader":
                self.leader_loop()

    def follower_loop(self):
        # listen for incoming requests from the leader, or timeout
        while self.state == "follower":
            self.initialize_election_timer()
            while self.timeout_thread.is_alive():

                # need to poll to see if we received anything back yet,
                # otherwise a cal to sock.recv() will block
                if self.rep_poll.poll():
                    req = self.rep_sock.recv_json()

                    if req["type"] == "RequestVotes":
                        print(f'RequestVotes from {req["addr"]} with term {req["term"]}')
                        self.reply_vote(req)
                    elif req["type"] == "AppendEntries":
                        pass
                    elif req["type"] == "InstallSnapshot":
                        pass

    def candidate_loop(self):
        """ The basic event loop for a candidate

        """
        while self.state == "candidate":
            print(f'In candidate loop!')

    def leader_loop(self):
        """ the basic event loop for a leader

        """
        while self.state == "leader":
            print(f'In candidate loop!')


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

        # initialize node with ip list and its own ip
        s = Server(my_ip, ip_list)
    else:
        print("usage: python raft.py <index> <ip_list_file>")
