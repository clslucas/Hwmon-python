# Script for python 3

import os
try:
    from utils import is_vm, print_dict
except Exception:
    from hwmon.utils import is_vm, print_dict

import subprocess

class Hwmon():

    def __init__(self):
        is_vm()

    class HW():
        def __init__(self):
            self.master_path = '/sys/class/hwmon'
            self.attributes_list = ["_max", "_min", "_crit", "_lcrit"]

        def value_format(self, attributes_file, value):

             # See https://www.kernel.org/doc/Documentation/hwmon/sysfs-interface
            if attributes_file.lower().startswith('in'):
                return str(int(value) / 1000) + ' V'
            elif attributes_file.lower().startswith('fan'):
                return value + ' RPM'
            elif attributes_file.lower().startswith('pwm'):
                return str(int(value) / 255) + ' PWM (%)'
            elif attributes_file.lower().startswith('temp'):
                return str(int(value) / 1000) + ' C'
            elif attributes_file.lower().startswith('curr'):
                return str(int(value) / 1000) + ' A'
            elif attributes_file.lower().startswith('power'):
                return str(int(value) / 1000000) + ' W'
            elif attributes_file.lower().startswith('freq'):
                return str(int(value) / 1000000) + ' MHz'

        def read_data(self, data_path):
            file = open(data_path, 'r')
            data = file.read().strip()
            file.close()
            return data

        def extract_data(self, sub_folder_path, file_):

            # initial hwmon data list
            hwmon_data = []
            data = dict()
            # split file header
            file_key = file_.split('_')[0]

            # read in/fan/temp/curr/power/energy/humidity[0-*]_input data
            if os.path.exists(os.path.join(sub_folder_path, file_key + '_label')):

                label_name = file_key + '_label'

                label_name = self.read_data(os.path.join(sub_folder_path, label_name))
                # only read input data, not to read the "*_input_highest" and "*_input_lowest"
                if '_input_' not in file_:
                    value = self.read_data(os.path.join(sub_folder_path, file_))

            else:

                label_name = file_key
                value = self.read_data(os.path.join(sub_folder_path, file_))

            data[label_name] = self.value_format(file_, value)
            hwmon_data.append(data)

            for file in self.attributes_list:
                file_id = file_key + file
                file_name = label_name + file
                if os.path.exists(os.path.join(sub_folder_path, file_id)):
                    value = self.read_data(os.path.join(sub_folder_path, file_id))
                    data[file_name] = self.value_format(file_id, value)
                    hwmon_data.append(data)

            return hwmon_data

        def data(self):

            data = dict()

            folders = os.listdir(self.master_path)

            for folder in folders:

                name_key = None
                sub_folder_path = os.path.join(self.master_path, folder)

                files = os.listdir(sub_folder_path)

                if os.path.exists(os.path.join(sub_folder_path, 'name')):
                    name_key = self.read_data(os.path.join(sub_folder_path, 'name'))

                symlink = os.readlink(os.path.join(sub_folder_path, 'device'))
                symlink = symlink.strip().split("/")[-1]
                sensor_name = f"{name_key}-{symlink}"

                data[sensor_name] = dict()

                for file_ in files:

                    try:

                        if '_input' in file_:
                            hwmon_data = self.extract_data(sub_folder_path, file_)
                            for label_name in hwmon_data:
                                data[sensor_name].update(label_name)

                        if '_average' in file_:
                            hwmon_data = self.extract_data(sub_folder_path, file_)
                            for label_name in hwmon_data:
                                data[sensor_name].update(label_name)

                    except Exception:
                        pass

                estimate_w = []

                for sensor in data.keys():

                    for value in data[sensor].keys():

                        if data[sensor][value].endswith("v"):

                            try:
                                v = float(data[sensor][value].split(" ")[0])
                                i = float(data[sensor]["I" + value[1:]].split(" ")[0])
                                estimate_w.append([sensor, "W" + value[1:] + "*", round(v*i,4)])
                            except Exception:
                                pass

                for value in estimate_w:
                    data[value[0]][value[1]] = str(value[2]) + " w"

            return data

        def print_data(self, colors=True):
            print_dict(self.data(), indent=0, colors=colors)

    class CPU():

        def __init__(self):

            self.path = '/proc/cpuinfo'

        def raw_data(self):

            data_file = open(self.path, 'r')
            data = data_file.readlines()
            data_file.close()

            manipulate_data = lambda data: data.strip().replace('\t', '').split(': ')
            data = list(map(manipulate_data, data))

            return data

        # See https://rosettacode.org/wiki/Linux_CPU_utilization#Python
        def cpu_usage(self):

            try:
                file = open("cpu.txt", "r")
                data = file.read().strip().split(";")
                last_idle, last_total = float(data[0]), float(data[1])
                file.close()
            except Exception:
                last_idle, last_total = 0, 0

            with open('/proc/stat') as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            idle, total = fields[3], sum(fields)
            idle_delta, total_delta = idle - last_idle, total - last_total
            last_idle, last_total = idle, total
            utilisation = 100.0 * (1.0 - idle_delta / total_delta)

            file = open("cpu.txt", "w")
            file.write(str(last_idle) + ";" + str(last_total))
            file.close()

            return utilisation

        def data(self):

            data = self.raw_data()
            mhz_sum, cont = 0, 0

            info = {'Name': '', 'CPU_usage': round(self.cpu_usage(), 2),
                    'cores': '', 'threads': '', 'cpu MHz':{}
                    }
            try:
                # Try to get the name in spanish
                info["Max MHz"] = int(float(subprocess.getstatusoutput(f"lscpu | grep 'CPU MHz máx'")[1].split()[-1].replace(",",".")))
            except IndexError:
                # Get the english name
                info["Max MHz"] = int(float(subprocess.getstatusoutput("lscpu | grep 'CPU max MHz'")[1].split()[-1].replace(",", ".")))
            except:
                info["Max MHz"] = None

            try:
                # Try to get the name in spanish
                info["Min MHz"] = int(float(subprocess.getstatusoutput(f"lscpu | grep 'CPU MHz mín'")[1].split()[-1].replace(",",".")))
            except IndexError:
                # Get the english name
                info["Min MHz"] = int(float(subprocess.getstatusoutput("lscpu | grep 'CPU min MHz'")[1].split()[-1].replace(",", ".")))
            except:
                info["Min MHz"] = None

            for line in data:

                if len(line) > 1:
                    if line[0] == 'model name' and info['Name'] == '':
                        info['Name'] = line[1]
                    elif line[0] == 'cpu MHz':
                        info['cpu MHz'][cont] = float(line[1])
                        mhz_sum = mhz_sum + float(line[1])
                        cont = cont + 1
                    elif line[0] == 'siblings' and info['threads'] == '':
                        info['threads'] = line[1]
                    elif line[0] == 'cpu cores' and info['cores'] == '':
                        info['cores'] = line[1]
                    else:
                        pass

            info['Average_MHz'] = round(mhz_sum / cont, 2)

            return info

        def print_data(self, colors=False):
            print_dict(self.data(), indent=0, colors=colors)

    class MEM():

        def __init__(self):

            self.path = '/proc/meminfo'

        def data(self):

            data_file = open(self.path, 'r')
            data = data_file.readlines()
            data_file.close()

            manipulate_data = lambda data: data.strip().replace('\t', '').replace(' ', '').replace('kB', '').split(':')
            data = list(map(manipulate_data, data))

            for i in range(len(data)):
                data[i][1] = self.convert_to_mb(float(data[i][1]))

            return dict(data)

        def print_data(self, colors=False):
            print_dict(self.data(), indent=0, colors=colors)

        def convert_to_mb(self, byte_size):
            """
                ref: https://gist.github.com/Pobux/0c474672b3acd4473d459d3219675ad8
                A bit is the smallest unit, it's either 0 or 1
                1 byte = 1 octet = 8 bits
                1 kB = 1 kilobyte = 1000 bytes = 10^3 bytes
                1 KiB = 1 kibibyte = 1024 bytes = 2^10 bytes
                1 KB = 1 kibibyte OR kilobyte ~= 1024 bytes ~= 2^10 bytes (it usually means 1024 bytes but sometimes it's 1000... ask the sysadmin ;) )
                1 kb = 1 kilobits = 1000 bits (this notation should not be used, as it is very confusing)
                1 ko = 1 kilooctet = 1000 octets = 1000 bytes = 1 kB
                Also Kb seems to be a mix of KB and kb, again it depends on context.
                In linux, a byte (B) is composed by a sequence of bits (b). One byte has 256 possible values.
                More info : http://www.linfo.org/byte.html
                """
            BASE_SIZE = 1024.00
            MEASURE = ["B", "KB", "MB", "GB", "TB", "PB"]

            def _fix_size(size, size_index):
                if not size:
                    return "0"
                elif size_index == 0:
                    return str(size)
                else:
                    return "{:.3f}".format(size)

            current_size = byte_size
            size_index = 0

            while current_size >= BASE_SIZE and len(MEASURE) != size_index:
                current_size = current_size / BASE_SIZE
                size_index = size_index + 1

            size_to_return = _fix_size(current_size, size_index)
            measure = MEASURE[size_index]
            return size_to_return + measure

    class NET():

        def __init__(self):

            self.path = '/proc/net/dev'

        def data(self):

            def remove_spaces(list_data):

                while '' in list_data:
                    list_data.remove('')

                return list_data

            data_file = open(self.path, 'r')
            data = data_file.readlines()[1:]
            data_file.close()

            info = dict()
            receive, transmit = remove_spaces(data[0].split('|')[1].split(' ')), remove_spaces(
                data[0].split('|')[2].strip().split(' '))

            for value in data[1:]:
                aux = value.split(':')
                name, stats = aux[0], list(map(int, remove_spaces(aux[1].strip().split(' '))))

                info[name] = dict()
                info[name]['receive'] = dict(zip(receive, stats[:8]))
                info[name]['transmit'] = dict(zip(transmit, stats[9:]))

            return info

        def print_data(self, colors=False):
            print_dict(self.data(), indent=0, colors=colors)

    class USB():

        def __init__(self):
            self.path = '/dev/input/by-id'

        def data(self):
            devices = list(map(lambda data: data.split('-event')[0], os.listdir(self.path)))
            return list(set(devices))

        def print_data(self):
            for device in self.data():
                print(device)

    class DISK():

        def __init__(self):
            self.path = '/dev/disk/by-id'

        def data(self):
            devices = list(map(lambda data: data.split('-part')[0], os.listdir(self.path)))
            return list(set(devices))

        def print_data(self):
            for device in self.data():
                print(device)

    class GPU():

        def __init__(self):
            self.master_path = ["/sys/class/graphics/", "/sys/class/drm/card0/device/"]

        def convert_to_mb(self, byte_size):
            """
                ref: https://gist.github.com/Pobux/0c474672b3acd4473d459d3219675ad8
                A bit is the smallest unit, it's either 0 or 1
                1 byte = 1 octet = 8 bits
                1 kB = 1 kilobyte = 1000 bytes = 10^3 bytes
                1 KiB = 1 kibibyte = 1024 bytes = 2^10 bytes
                1 KB = 1 kibibyte OR kilobyte ~= 1024 bytes ~= 2^10 bytes (it usually means 1024 bytes but sometimes it's 1000... ask the sysadmin ;) )
                1 kb = 1 kilobits = 1000 bits (this notation should not be used, as it is very confusing)
                1 ko = 1 kilooctet = 1000 octets = 1000 bytes = 1 kB
                Also Kb seems to be a mix of KB and kb, again it depends on context.
                In linux, a byte (B) is composed by a sequence of bits (b). One byte has 256 possible values.
                More info : http://www.linfo.org/byte.html
                """
            BASE_SIZE = 1024.00
            MEASURE = ["B", "KB", "MB", "GB", "TB", "PB"]

            def _fix_size(size, size_index):
                if not size:
                    return "0"
                elif size_index == 0:
                    return str(size)
                else:
                    return "{:.2f}".format(size)

            current_size = byte_size
            size_index = 0

            while current_size >= BASE_SIZE and len(MEASURE) != size_index:
                current_size = current_size / BASE_SIZE
                size_index = size_index + 1

            size_to_return = _fix_size(current_size, size_index)
            measure = MEASURE[size_index]
            return size_to_return + measure

        def data(self):

            for master_path in self.master_path:

                try:
                    data = dict()

                    folders = os.listdir(master_path)

                    for folder in folders:

                        sub_folder_path = os.path.join(master_path, folder)

                        files = os.listdir(sub_folder_path)

                        if "name" in files:

                            name = open(os.path.join(sub_folder_path, 'name'), 'r')
                            name_key = name.read().strip()
                            name.close()

                            data[name_key] = dict()

                            gpu_name = subprocess.getstatusoutput("lspci -v | egrep -i --color 'vga|3d|2d'")[1]

                            for gpu_call in gpu_name:

                                if "VGA" in gpu_call:
                                    data[name_key]["Name"] = gpu_call.split(":")[2]

                            data[name_key]["Resolution"] = subprocess.getstatusoutput("xdpyinfo  | grep 'dimensions:'")[1].split(":")[1].replace("    ","")

                            sub_folder_path = os.path.join(master_path, folder, "device")
                            files = os.listdir(sub_folder_path)

                            for file in files:

                                if "current_link" in file or "busy" in file or "mem_" in file or "bios" in file:

                                    data_file = open(os.path.join(sub_folder_path, file), 'r')
                                    data_read = data_file.read().strip()
                                    data_file.close()

                                    try:
                                        if "mem_" in file and "percent" not in file:

                                                data_read = self.convert_to_mb(int(data_read))

                                        if "percent" in file:
                                            data_read = data_read + " %"
                                        data[name_key][file] = data_read

                                    except Exception:
                                        pass

                    return data

                except Exception as e:
                    print(e)
                    pass

        def print_data(self, colors=False):
            print_dict(self.data(), indent=0, colors=colors)

    class BIOS():

        def __init__(self):

            self.master_path = "/sys/class/dmi/id/"

        def data(self):

            data = dict()

            files = os.listdir(self.master_path)

            for file in files:

                if "bios" in file or "board" in file or "chassis" in file or "product" in file or "vendor" in file:
                    try:
                        data_file = open(os.path.join(self.master_path, file), 'r')
                        data_read = data_file.read().strip()
                        data_file.close()

                        if "To Be Filled By O.E.M." not in data_read:
                            data[file] = data_read
                    except Exception:
                        pass

            return data

        def print_data(self, colors=False):
            print_dict(self.data(), indent=0, colors=colors)

#print(Hwmon().HW().data())
#print(Hwmon().HW().print_data())
#print(Hwmon().CPU().data())
#print(Hwmon().CPU().print_data())
#print(Hwmon().MEM().data())
#print(Hwmon().MEM().print_data())
#print(Hwmon().NET().data())
#print(Hwmon().NET().print_data())
#print(Hwmon().USB().data())
#print(Hwmon().USB().print_data())
#print(Hwmon().DISK().data())
#print(Hwmon().DISK().print_data())
#print(Hwmon().GPU().data())
#print(Hwmon().GPU().print_data())
#print(Hwmon().BIOS().data())
#print(Hwmon().BIOS().print_data())
