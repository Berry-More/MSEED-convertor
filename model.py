import os
import numpy as np
import obspy as obs
import struct as st


# Понасенко Святослав
# 7 января 2023
# Функции чтения файлов формата "SCOUT"
# Во время записи для каждого канала создается отдельный файл. 1 измерение = 3 файла


def time(path, file):
    return obs.UTCDateTime(int(path[-13:-9]), int(path[-8:-6]), int(path[-5:-3]), int(path[-2:]),
                           int(file[:2]), int(file[2:4]), int(file[5:11]))


def add_avg_with_border(a, avg, border):
    if a < border:
        a = avg + a
    else:
        a = avg + (a - ((border + 1) * 2))
    return a


def find_len(file_set):
    f = open(file_set, 'rb')
    bits = 40
    b = st.unpack(str(bits) + 's', f.read(bits))[0]
    while not(b'\r\n' in b[-3:]):
        if b'\r\n' in b[-3:]:
            continue
        else:
            bits += 1
            f = open(file_set, 'rb')
            b = st.unpack(str(bits) + 's', f.read(bits))[0]
    bits += 1
    b = st.unpack(str(bits) + 's', f.read(bits))[0]
    while not(b'\r\n' in b[-3:]):
        if b'\r\n' in b[-3:]:
            continue
        else:
            bits += 1
            f = open(file_set, 'rb')
            b = st.unpack(str(bits) + 's', f.read(bits))[0]
    return len(b)


def read_scout(path, file_name, return_meta=False):
    
    file_set = os.path.join(path, file_name)
    head_len = find_len(file_set)
    data_all = np.empty(0, dtype=np.int32)               # массив с данными
    
    with open(file_set, 'rb') as f:
        block_number = st.unpack('i', f.read(4))[0]      # Заводской номер блока           
        rec_time = st.unpack('i', f.read(4))[0]          # Время записи в милисекундах
        quantum_time = st.unpack('f', f.read(4))[0]      # Период квантования
        f.read(4)
        f.read(4)
        receiving_line = st.unpack('i', f.read(4))[0]    # Линия приема первого канала
        rec_picket = st.unpack('i', f.read(4))[0]        # Пикет приема
        components = st.unpack('i', f.read(4))[0]        # Число компонент датчика
        channel = st.unpack('i', f.read(4))[0]           # Номер канала
        f.read(4)
        
        head_len = head_len - 40
        a = str(st.unpack(str(head_len) + 's', f.read(head_len))[0])[20:50]
        for i in range(len(a)):
            if a[i] == 'N':
                lat = float(a[i-10:i-1])                # latitude
            if a[i] == 'E':
                lon = float(a[i-10:i-1])                # longitude

        for i in range(rec_time // 1000):               # Далее данные идут блоками, в каждом блоке есть шапка и данные

            type_comp = st.unpack('b', f.read(1))[0]    # Тип данных в блоке
            f.read(1)
            data_count = st.unpack('h', f.read(2))[0]   # количество значений
            avg = st.unpack('i', f.read(4))[0]          # среднее значение с которым мы складываем
            
            if type_comp == 0:
                data = np.fromfile(f, dtype='b', count=data_count)
                data = avg + (data - ((data >= 127).astype(np.int32) * 256))
                data_all = np.concatenate((data_all, data), axis=0)

            elif type_comp == 1:
                data_shape = data_count + data_count // 2
                data = np.empty(data_count, dtype=np.int32)
                b = f.read(data_shape)
                for k, j in zip(range(0, data_shape, 3), range(0, data_count, 2)):
                    b0, b1, b2 = b[k:k+3]
                    a2 = ((b2 << 4) & 0b111100000000) + b1
                    a1 = ((b2 << 8) & 0b111100000000) + b0

                    a2 = add_avg_with_border(a2, avg, 2047)
                    a1 = add_avg_with_border(a1, avg, 2047)

                    data[j:j + 2] = a1, a2
                data_all = np.concatenate((data_all, data))

            elif type_comp == 2:
                data = np.fromfile(f, dtype=np.int16, count=data_count)
                data = avg + (data - ((data >= 32767).astype(np.int32) * 65536))
                data_all = np.concatenate((data_all, data))

            elif type_comp == 3:
                data = np.empty(data_count, dtype=np.int32)
                data_shape = data_count * 3
                b = f.read(data_shape)

                for k in range(0, data_shape, 3):
                    a3, a2, a1 = ((b[k + j] << (j * 8)) for j in range(3))
                    w = add_avg_with_border((a1 | a2 | a3), avg, 8388607)
                    data[k // 3] = w
                data_all = np.concatenate((data_all, data))
            
            else:
                raise TypeError('bad type')

        if return_meta:
            meta = {'block_num': block_number, 'quantum_time': quantum_time, 'rec_line': receiving_line,
                    'rec_picket': rec_picket, 'components': components, 'channel': channel,
                    'latitude': lat/100, 'longitude': lon/100, 'time': time(path, file_name)}

            return meta, data_all
        else:
            return data_all


def convert_3_components(path_input, path_output):
    files = os.listdir(path_input)
    streams = {'1': obs.Stream(), '2': obs.Stream(), '3': obs.Stream()}

    for file_name in files:
        meta, data = read_scout(path_input, file_name, return_meta=True)

        header = {'station': str(meta['block_num']), 'network': 'XX', 'location': 'XX',
                  'channel': file_name[-5], 'npts': len(data), 'sampling_rate': meta['quantum_time'],
                  'starttime': meta['time'], 'mseed': {'dataquality': 'R'}}

        streams[file_name[-5]].append(obs.Trace(data=data, header=header))

    for i in streams:
        write_name = streams[i][0].stats.starttime.strftime('%Y%m%d_%H%M%S_') + streams[i][0].stats.station
        write_name = write_name + '_CH' + i
        streams[i].write(os.path.join(path_output, write_name))
