"""Offline EA F1 23 v1 packet fixture parser. Live UDP integration is deferred.
Specification: https://forums.ea.com/discussions/f1-23-en/f1-23-udp-specification/8390745
Unsupported game formats are rejected, not interpreted as F1 23.
"""
import struct,math
DEFAULT_PORT=20777
HEADER_FORMAT='<HBBBBBQfIIBB';HEADER_SIZE=struct.calcsize(HEADER_FORMAT)
CAR_FORMAT='<HfffBbHBBH4H4B4BH4f4B';CAR_SIZE=struct.calcsize(CAR_FORMAT)
class F1UDPReceiver:
    def __init__(self,port=DEFAULT_PORT,host='127.0.0.1'):self.port=port;self.host=host;self.sock=None;self.is_running=False
    def parse_header(self,data):
        if len(data)<HEADER_SIZE:return None
        u=struct.unpack_from(HEADER_FORMAT,data)
        if u[0]!=2023 or u[1]!=23 or u[4]!=1 or u[5]!=6 or u[10]>=22:return None
        if not math.isfinite(u[7]):return None
        return {'packet_format':u[0],'game_year':u[1],'game_major':u[2],'game_minor':u[3],'packet_version':u[4],'packet_id':u[5],'session_uid':u[6],'session_time':u[7],'frame_identifier':u[8],'overall_frame_identifier':u[9],'player_car_index':u[10],'secondary_player_car_index':u[11]}
    def parse_car_telemetry(self,data,player_index):
        if self.parse_header(data) is None or not isinstance(player_index,int) or not 0<=player_index<22 or len(data)!=HEADER_SIZE+22*CAR_SIZE+3:return None
        u=struct.unpack_from(CAR_FORMAT,data,HEADER_SIZE+player_index*CAR_SIZE)
        speed,throttle,steer,brake,clutch,gear,rpm=u[:7]
        if not all(math.isfinite(v) for v in (throttle,steer,brake)) or not 0<=throttle<=1 or not 0<=brake<=1 or not -1<=steer<=1 or not -1<=gear<=8:return None
        return {'speed':float(speed),'throttle':float(throttle),'steer':float(steer),'brake':float(brake),'gear':int(gear),'rpm':int(rpm)}
    def start_socket(self):raise RuntimeError('Live UDP is deferred. Use recorded JSON replay; only offline F1 23 v1 fixtures are supported.')
    def close(self):
        self.is_running=False
        if self.sock:self.sock.close()
