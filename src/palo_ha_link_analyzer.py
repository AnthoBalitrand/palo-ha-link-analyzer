import xmltodict
from panos.firewall import Firewall
from rich.prompt import Prompt 
from rich.console import Console 
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.layout import Layout 
import datetime
import time

palo_ip = ""
palo_username = ""
palo_password = "" 
update_interval = ""
palo_connection = None

msg_sizes = {
	"session": 400, 
	"arp": 52, 
	"mac": 52, 
	"ipsec": 48
}

header_size = 28


def bw_calc(tt1, tt2, msg_desc, incr): 
	time_delta = tt1 - tt2
	msec_delta = time_delta.total_seconds()

	try:
		msg_sz = [v for k, v in msg_sizes.items() if k in msg_desc.lower()][0]
		exchange_size = (msg_sz + header_size) * incr #bytes
		exchange_size_bits = exchange_size * 8 #bits
		bits_sec = exchange_size_bits / msec_delta

		return round(bits_sec / 1048576, 3)
		#return int(exchange_size / msec_delta / 1000)
	except Exception as e: 
		return 'NA'


try:
	while palo_ip == "":
		palo_ip = Prompt.ask("Palo Alto appliance IP ? ")

	while palo_username == "":
		palo_username = Prompt.ask("Username for API connection ?")

	while palo_password == "":
		palo_password = Prompt.ask("Password for API connection ?", password=True)

	while update_interval == "":
		update_interval = int(Prompt.ask("Values update interval ?"))
	
	palo_connection = Firewall(palo_ip, palo_username, palo_password)
	prev_o = None
	prev_dt = None

	#console = Console()
	layout = Layout()

	layout.split(
		Layout(ratio=1, name="main"))

	layout["main"].split_row(
		Layout(name="session info"),
		Layout(name="sync info"))

	#console.print(layout)

	with Live(layout, screen=True) as live_table:

		while True:
			o = xmltodict.parse(palo_connection.op("show high-availability state-synchronization", xml=True))
			o2 = xmltodict.parse(palo_connection.op("show session info", xml=True))
			start_dt = datetime.datetime.now()

			table_session = Table(title="Session count")
			table_session.add_column("Info")
			table_session.add_column("Value")

			for k, v in sorted(o2["response"]["result"].items()):
				table_session.add_row(k, v)

			table = Table(title="State-synchronization")
			table.add_column("Sync type")
			table.add_column("Msgs sent")
			table.add_column("Msgs sent incr")
			table.add_column("Msgs sent BW Mbps")
			table.add_column("Msgs received")
			table.add_column("Msgs received incr")
			table.add_column("Msgs received BW Mbps")

			row_num = 0
			for sync_t in o["response"]["result"]["messages"]["entry"]:
				if prev_o:
					table.add_row(
						sync_t['desc'], 
						sync_t['sent'], 
						(incr1 := str(int(sync_t['sent']) - int(prev_o[row_num]['sent']))), 
						str(bw_calc(start_dt, prev_dt, sync_t['desc'], int(incr1))),
						sync_t['recv'], 
						(incr2 := str(int(sync_t['recv']) - int(prev_o[row_num]['recv']))), 
						str(bw_calc(start_dt, prev_dt, sync_t['desc'], int(incr2))))
				else:
					table.add_row(
						sync_t['desc'], 
						sync_t['sent'],
						'NA',
						'NA',
						sync_t['recv'],
						'NA', 
						'NA')

				row_num+=1
			layout['session info'].update(Align.right(table))
			layout['sync info'].update(Align.left(table_session))

			prev_o = o["response"]["result"]["messages"]["entry"]
			prev_dt = start_dt

			time.sleep(update_interval)

except KeyboardInterrupt:
	exit(0)

except Exception as e:
	print(f"Exception when connecting to appliance : {e}")