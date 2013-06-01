from argparse import ArgumentParser

from relayserver.main import start_relay

def main():
    parser = ArgumentParser(description='Start a protocol-agnostic relay '
                                        'server.')

    parser.add_argument('dport', 
                        nargs='?', 
                        default=8000, 
                        type=int, 
                        help="Port for host-process data-channel connections.")

    parser.add_argument('cport', 
                        nargs='?', 
                        default=8001, 
                        type=int, 
                        help="Port for host-process command-channel "
                             "connections.")

    parser.add_argument('tport', 
                        nargs='?', 
                        default=8002, 
                        type=int, 
                        help="Port for client data-channel connections.")

    args = parser.parse_args()

    start_relay(args.dport, args.cport, args.tport)

if __name__ == '__main__':
    main()
