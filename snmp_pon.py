from easysnmp import Session, EasySNMPTimeoutError
from onu_adress import ip_adress
from flask import Flask, render_template
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 10
executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
print(time.strftime('%X'))
app = Flask(__name__)


class MySnmp:

    def __init__(self, ip):
        self.response_model = None
        self.__session = Session(hostname=str(ip), community='cisco123', version=2, timeout=3, retries=1)

    def get_name(self):
        try:
            response_name = self.__session.get('.1.3.6.1.2.1.1.5.0').value
            if "EPON" in response_name or "GPON" in response_name:
                self.response_model = response_name
                return response_name
        except EasySNMPTimeoutError:
            pass

    def get_ports(self):

        self.count = 0
        self.response_model = self.__session.get('.1.3.6.1.2.1.1.1.0').value
        if 'BDCOM(tm) P3310C' in self.response_model or 'BDCOM(tm) P3310D' in self.response_model or 'ELTEX LTP-4X-rev.C' in self.response_model:
            self.count = 4
            return self.count
        else:
            self.count = 8
            return self.count

    def get_onu_quantity(self):
        data = {}
        self.__session.use_numeric = True
        if 'BDCOM' in self.response_model:
            self.__session.timeout = 1
            result_epon = self.__session.walk('1.3.6.1.4.1.3320.101.11.4.1.5')
            for epon in result_epon:
                if self.count == 4:
                    epon_port = int(epon.oid.split('.')[-1]) - 14
                    data[epon_port] = data.setdefault(epon_port, 0) + 1
                else:
                    if 'P3608B' in self.response_model:
                        epon_port = int(epon.oid.split('.')[-1]) - 75
                    else:
                        epon_port = int(epon.oid.split('.')[-1]) - 46
                    data[epon_port] = data.setdefault(epon_port, 0) + 1
        else:
            result_gpon = self.__session.walk(".1.3.6.1.4.1.35265.1.22.3.80.1.4.1")
            for gpon in result_gpon:
                gpon_port = int(gpon.oid.split('.')[-1])
                if data.get(gpon_port) is None:
                    data[gpon_port] = 1
                else:
                    data[gpon_port] += 1
            pass
        return data

    def get_data(self, ip):
        snmp = MySnmp(ip)
        name = snmp.get_name()
        if name is not None:
            return {
                'name': name,
                'ip': ip,
                'ports': snmp.get_ports(),
                'onu_quantity': snmp.get_onu_quantity()
            }


@app.route("/")
def start():
    html = list()
    with executor as pool:
        # Запускаем опросы в пуле потоков
        future_results = [pool.submit(MySnmp(ip).get_data, ip) for ip in ip_adress()]
        for future in future_results:
            result = future.result()
            if result is not None:
                html.append(result)

    return render_template('index.html', data=html)


if __name__ == '__main__':
    print(time.strftime('%X'))
    app.run(threaded=True, debug=True, port=5001, host='0.0.0.0')
