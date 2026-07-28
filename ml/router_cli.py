"""
router_cli.py -- thin command-line wrapper so the Node backend can call the router.
Usage:  python router_cli.py "one cheeseburger please"
Prints one JSON line:  {"route":"execute","reason":"type:simple","type":"simple","confidence":0.71}
"""
import sys, json
from router_demo import route_order

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"route": "clarify", "reason": "no_input", "type": None, "confidence": None}))
        sys.exit(0)
    try:
        print(json.dumps(route_order(sys.argv[1])))
    except Exception as e:
        print(json.dumps({"route": "clarify", "reason": "exception", "type": None, "confidence": None, "error": str(e)}))
