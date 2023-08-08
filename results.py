import re
import statistics
"""
custom script for parsing results
"""
# lang = ['arith', 'fol', 'json', 'lisp', 'mathexpr', 'turtle', 'while', 'xml']
lang = ['json', 'lisp', 'turtle', 'while', 'xml']
prefix = 'z-'
for lan in lang:
    # print(lan)
    recall_arr, precision_arr, f1_arr, build_time_arr, oracle_time_arr, queries_arr, bubbling_arr, sampling_arr, memory_arr, reapply_arr, ptime_arr, pmem_arr = ([] for i in range(12))
    for i in range(0, 10):
        try:
            recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem = (False,)*12
            for line in open(f'micro-benchmarks/{prefix}{lan}-{i}.log.eval'):
                match = re.search('Recall: \d+\.\d+, Precision: \d+\.\d+', line)
                if match:
                    recall, precision = match.group().split()[1][:-1], match.group().split()[3]
                    f1 = 2 * float(recall) * float(precision) / (float(recall) + float(precision))
                    recall_arr.append(float(recall))
                    precision_arr.append(float(precision))
                    f1_arr.append(f1)
            for line in open(f'micro-benchmarks/{prefix}{lan}-{i}.log.eval2'):
                match = re.search('Scoring time: \d+\.\d+', line)
                if match:
                    ptime = match.group().split()[2]
                    ptime_arr.append(float(ptime)/1000)

        except Exception as e:
            print(e)
        try:
            for line in open(f'micro-benchmarks/{prefix}{lan}-{i}.log'):
                match = re.search('grammar: \d+\.\d+', line)
                if match:
                    build_time = match.group().split()[1]
                    build_time_arr.append(float(build_time)/1000)
                match = re.search('oracle calls: \d+\.\d+', line)
                if match:
                    oracle_time = match.group().split()[2]
                    oracle_time_arr.append(float(oracle_time)/1000)
                match = re.search('Parse calls: \d+', line)
                if match:
                    queries = match.group().split()[2]
                    queries_arr.append(int(queries)/1000)
                match = re.search('\'OVERALL_EXAMPLE_GEN\': \d+\.\d+', line)
                if match:
                    sampling = match.group().split()[1]
                    sampling_arr.append(float(sampling)/1000)
                match = re.search('\'OVERALL_GROUPING\': \d+\.\d+', line)
                if match:
                    bubbling = match.group().split()[1]
                    bubbling_arr.append(float(bubbling)/1000)
                match = re.search('\'REAPPLY_COUNT\': \d+', line)
                if match:
                    reapply = match.group().split()[1]
                    reapply_arr.append(int(reapply))
        except:
            continue
        
        try:
            for line in open(f'slog-{lan}-{i}'):
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    memory = int(match.group().split()[5])/(1024*1024)
                    memory_arr.append(float(memory))
            for line in open(f'tlog-{lan}-{i}'):
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    pmem = int(match.group().split()[5])/(1024*1024)
                    pmem_arr.append(float(pmem))
        except:
            continue

        # print(recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem)
    # print("AVG")
    print(statistics.mean(recall_arr), statistics.pstdev(recall_arr), statistics.mean(precision_arr), statistics.pstdev(precision_arr),
          statistics.mean(f1_arr), statistics.pstdev(f1_arr), statistics.mean(build_time_arr), statistics.pstdev(build_time_arr),
          statistics.mean(oracle_time_arr), statistics.pstdev(oracle_time_arr), statistics.mean(queries_arr), statistics.pstdev(queries_arr),
          statistics.mean(memory_arr), statistics.pstdev(memory_arr), statistics.mean(reapply_arr), statistics.pstdev(reapply_arr),
          statistics.mean(bubbling_arr), statistics.pstdev(bubbling_arr), statistics.mean(sampling_arr), statistics.pstdev(sampling_arr),
          statistics.mean(ptime_arr), statistics.pstdev(ptime_arr), statistics.mean(pmem_arr), statistics.pstdev(pmem_arr))

lang = ['curl', 'tinyc', 'nodejs']
prefix = 'z-'
for lan in lang:
    # print(lan)
    recall_arr, precision_arr, f1_arr, build_time_arr, oracle_time_arr, queries_arr, bubbling_arr, sampling_arr, memory_arr, reapply_arr, ptime_arr, pmem_arr = ([] for i in range(12))
    for i in range(0, 10):
        try:
            recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem = (False,)*12
            for line in open(f'{lan}/{prefix}{lan}-{i}.log.eval'):
                match = re.search('Recall: \d+\.\d+, Precision: \d+\.\d+', line)
                if match:
                    recall, precision = match.group().split()[1][:-1], match.group().split()[3]
                    f1 = 2 * float(recall) * float(precision) / (float(recall) + float(precision))
                    recall_arr.append(float(recall))
                    precision_arr.append(float(precision))
                    f1_arr.append(f1)

            for line in open(f'{lan}/{prefix}{lan}-{i}.log.eval2'):
                match = re.search('Scoring time: \d+\.\d+', line)
                if match:
                    ptime = match.group().split()[2]
                    ptime_arr.append(float(ptime)/1000)

            for line in open(f'{lan}/{prefix}{lan}-{i}.log'):
                match = re.search('grammar: \d+\.\d+', line)
                if match:
                    build_time = match.group().split()[1]
                    build_time_arr.append(float(build_time)/1000)
                match = re.search('oracle calls: \d+\.\d+', line)
                if match:
                    oracle_time = match.group().split()[2]
                    oracle_time_arr.append(float(oracle_time)/1000)
                match = re.search('Parse calls: \d+', line)
                if match:
                    queries = match.group().split()[2]
                    queries_arr.append(int(queries)/1000)
                match = re.search('\'OVERALL_EXAMPLE_GEN\': \d+\.\d+', line)
                if match:
                    sampling = match.group().split()[1]
                    sampling_arr.append(float(sampling)/1000)
                match = re.search('\'OVERALL_GROUPING\': \d+\.\d+', line)
                if match:
                    bubbling = match.group().split()[1]
                    bubbling_arr.append(float(bubbling)/1000)
                match = re.search('\'REAPPLY_COUNT\': \d+', line)
                if match:
                    reapply = match.group().split()[1]
                    reapply_arr.append(int(reapply))
        except Exception as e:
            print(e)
            continue
        try:
            for line in open(f'slog-{lan}-{i}'):
                # print(line)
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    memory = int(match.group().split()[5])/(1024*1024)
                    memory_arr.append(float(memory))
            for line in open(f'tlog-{lan}-{i}'):
                # print(line)
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    pmem = int(match.group().split()[5])/(1024*1024)
                    pmem_arr.append(float(pmem))
        except:
            continue

        # print(recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem)
    # print("AVG")
    print(statistics.mean(recall_arr), statistics.pstdev(recall_arr), statistics.mean(precision_arr), statistics.pstdev(precision_arr),
          statistics.mean(f1_arr), statistics.pstdev(f1_arr), statistics.mean(build_time_arr), statistics.pstdev(build_time_arr),
          statistics.mean(oracle_time_arr), statistics.pstdev(oracle_time_arr), statistics.mean(queries_arr), statistics.pstdev(queries_arr),
          statistics.mean(memory_arr), statistics.pstdev(memory_arr), statistics.mean(reapply_arr), statistics.pstdev(reapply_arr),
          statistics.mean(bubbling_arr), statistics.pstdev(bubbling_arr), statistics.mean(sampling_arr), statistics.pstdev(sampling_arr),
          statistics.mean(ptime_arr), statistics.pstdev(ptime_arr), statistics.mean(pmem_arr), statistics.pstdev(pmem_arr))
    
lang = ['tinyc', 'nodejs']
prefix = 'z10-'
for lan in lang:
    # print(lan, "10")
    recall_arr, precision_arr, f1_arr, build_time_arr, oracle_time_arr, queries_arr, bubbling_arr, sampling_arr, memory_arr, reapply_arr, ptime_arr, pmem_arr = ([] for i in range(12))
    for i in range(0, 10):
        try:
            recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem = (False,)*12
            for line in open(f'{lan}/{prefix}{lan}-{i}.log.eval'):
                match = re.search('Recall: \d+\.\d+, Precision: \d+\.\d+', line)
                if match:
                    recall, precision = match.group().split()[1][:-1], match.group().split()[3]
                    f1 = 2 * float(recall) * float(precision) / (float(recall) + float(precision))
                    recall_arr.append(float(recall))
                    precision_arr.append(float(precision))
                    f1_arr.append(f1)
            
            for line in open(f'{lan}/{prefix}{lan}-{i}.log.eval2'):
                match = re.search('Scoring time: \d+\.\d+', line)
                if match:
                    ptime = match.group().split()[2]
                    ptime_arr.append(float(ptime)/1000)
        except Exception as e:
            print(e)
        try:
            for line in open(f'{lan}/{prefix}{lan}-{i}.log'):
                match = re.search('grammar: \d+\.\d+', line)
                if match:
                    build_time = match.group().split()[1]
                    build_time_arr.append(float(build_time)/1000)
                match = re.search('oracle calls: \d+\.\d+', line)
                if match:
                    oracle_time = match.group().split()[2]
                    oracle_time_arr.append(float(oracle_time)/1000)
                match = re.search('Parse calls: \d+', line)
                if match:
                    queries = match.group().split()[2]
                    queries_arr.append(int(queries)/1000)
                match = re.search('\'OVERALL_EXAMPLE_GEN\': \d+\.\d+', line)
                if match:
                    sampling = match.group().split()[1]
                    sampling_arr.append(float(sampling)/1000)
                match = re.search('\'OVERALL_GROUPING\': \d+\.\d+', line)
                if match:
                    bubbling = match.group().split()[1]
                    bubbling_arr.append(float(bubbling)/1000)
                match = re.search('\'REAPPLY_COUNT\': \d+', line)
                if match:
                    reapply = match.group().split()[1]
                    reapply_arr.append(int(reapply))
        except:
            continue
        try:
            for line in open(f'slog10-{lan}-{i}'):
                # print(line)
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    memory = int(match.group().split()[5])/(1024*1024)
                    memory_arr.append(float(memory))
            for line in open(f'tlog10-{lan}-{i}'):
                # print(line)
                match = re.search('Maximum resident set size \(kbytes\): \d+', line)
                if match:
                    pmem = int(match.group().split()[5])/(1024*1024)
                    pmem_arr.append(float(pmem))

        except:
            continue

        # print(recall, precision, f1, build_time, oracle_time, queries, bubbling, sampling, memory, reapply, ptime, pmem)
    # print("AVG")
    print(statistics.mean(recall_arr), statistics.pstdev(recall_arr), statistics.mean(precision_arr), statistics.pstdev(precision_arr),
          statistics.mean(f1_arr), statistics.pstdev(f1_arr), statistics.mean(build_time_arr), statistics.pstdev(build_time_arr),
          statistics.mean(oracle_time_arr), statistics.pstdev(oracle_time_arr), statistics.mean(queries_arr), statistics.pstdev(queries_arr),
          statistics.mean(memory_arr), statistics.pstdev(memory_arr), statistics.mean(reapply_arr), statistics.pstdev(reapply_arr),
          statistics.mean(bubbling_arr), statistics.pstdev(bubbling_arr), statistics.mean(sampling_arr), statistics.pstdev(sampling_arr),
          statistics.mean(ptime_arr), statistics.pstdev(ptime_arr), statistics.mean(pmem_arr), statistics.pstdev(pmem_arr))