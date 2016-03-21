def sim_hash(trace, limit=512):
    if trace:
        result = 0
        lines = trace.split('\r?\n')
        words = []
        for line in lines:
            word_list = line.split()
            filter_list = [word for word in word_list if len(word) > 0]
            words.extend(filter_list)

        split_set = set(words)
        # preserve ordering when computing the split list
        split_list = [word for word in words if word in split_set]
        for i in range(min(len(split_list), limit)):
            result ^= hash(split_list[i])
        return unicode(result)
    else:
        return None


def main():
    trace_1 = '''
                Error: Error message
                    at null._onTimeout (/examples/error-module.js:7:29)
                    at Timer.listOnTimeout [as ontimeout] (timers.js:110:15)
              '''
    trace_2 = '''
                Error: Error message
                    at console._onTimeout (/examples/error-module.js:7:29)
                    at Timer.listOnTimeout [as ontimeout] (timers.js:110:15)
              '''
    print('sim_hash  = %s' % (sim_hash(trace_1)))
    print('sim_hash  = %s' % (sim_hash(trace_2)))


if __name__ == '__main__':
    main()
