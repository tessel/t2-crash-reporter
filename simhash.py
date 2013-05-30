'''
Computes the sim has of a given string.
'''
def sim_hash(input, limit=512):
    if input:
        result = 0
        lines = input.split('(\n|\r|(\r\n))')
        words = []
        for line in lines:
            word_list = line.split()
            filter_list = [word for word in word_list if len(word) > 0]
            words.extend(filter_list)

        split_set = list(set(words))
        for i in range(min(len(split_set), limit)):
            result =  result ^ hash(split_set[i])

        return result
    else:
        return None

def main():
    val_1 = '''
                The quick brown fox jumped over the lazy dog
                The quick brown fox jumped over the lazy dog
            '''
    val_2 = '''
                The quick brown fox jumped dog the lazy over
                The quick brown fox jumped dog the lazy over
            '''
    print('sim_hash  = %s' % (sim_hash(val_1)))
    print('sim_hash  = %s' % (sim_hash(val_2)))

if __name__ == '__main__':
    main()
