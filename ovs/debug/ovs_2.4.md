

## ovs 2.4.0 版本测试


### 基于 IP 的负载均衡

IP 范围 10.2.1.100~10.2.1.115 10.2.1.150~10.2.1.165

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns begin at 2017年 05月 19日 星期五 09:18:56 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
[查看cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns结果](http://10.9.1.8:9090/dashboard/db/ab-monitor?from=1495156739000&to=1495158441000)
case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns end at 2017年 05月 19日 星期五 09:39:06 CST
bench loadbalance vip 10.2.1.200 with four server 10.2.1.40-44


IP 范围 10.2.1.100~10.2.1.129 10.2.1.150~10.2.1.179

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns begin at 2017年 05月 19日 星期五 09:40:37 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
[查看cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns结果](http://10.9.1.8:9090/dashboard/db/ab-monitor?from=1495158041000&to=1495159745000)
case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns end at 2017年 05月 19日 星期五 10:00:53 CST


IP 范围 10.2.1.100~10.2.1.139 10.2.1.150~10.2.1.189

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns begin at 2017年 05月 19日 星期五 10:02:36 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
bench loadbalance vip 10.2.1.200 with four server 10.2.1.40-44

IP 范围 10.2.1.100~10.2.1.199

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns begin at 2017年 05月 19日 星期五 10:10:32 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
[查看cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns结果](http://10.9.1.8:9090/dashboard/db/ab-monitor?from=1495159836000&to=1495161543000)
case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns end at 2017年 05月 19日 星期五 10:30:55 CST

case cores=2 concurrent=500:100:500 total_request=1200 url_path=50.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns begin at 2017年 05月 19日 星期五 10:35:55 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
bench loadbalance vip 10.2.1.200 with four server 10.2.1.40-44

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns begin at 2017年 05月 19日 星期五 10:43:13 CST
10.2.1.40-flows: 20
10.2.1.41-flows: 20
10.2.1.42-flows: 20
10.2.1.43-flows: 20
10.2.1.44-flows: 20
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
bench loadbalance vip 10.2.1.200 with four server 10.2.1.40-44

### 基于端口范围的负载均衡

端口分段 1024
IP 范围 10.2.1.100~10.2.1.199

case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns begin at 2017年 05月 19日 星期五 11:02:30 CST
10.2.1.40-flows: 1200
10.2.1.41-flows: 1300
10.2.1.42-flows: 1300
10.2.1.43-flows: 1300
10.2.1.44-flows: 1300
10.2.1.45-flows: 0
10.9.1.48-handler-thread: "4"
10.9.1.48-revaildator-thread: "4"
[查看cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns结果](http://10.9.1.8:9090/dashboard/db/ab-monitor?from=1495162954000&to=1495164671000)
case cores=2 concurrent=500:100:500 total_request=1200 url_path=10.html namespace=client100_ns,client101_ns,client102_ns,client103_ns,client104_ns,client105_ns,client106_ns,client107_ns,client108_ns,client109_ns,client110_ns,client111_ns,client112_ns,client113_ns,client114_ns,client115_ns,client116_ns,client117_ns,client118_ns,client119_ns,client120_ns,client121_ns,client122_ns,client123_ns,client124_ns,client125_ns,client126_ns,client127_ns,client128_ns,client129_ns,client130_ns,client131_ns,client132_ns,client133_ns,client134_ns,client135_ns,client136_ns,client137_ns,client138_ns,client139_ns,client140_ns,client141_ns,client142_ns,client143_ns,client144_ns,client145_ns,client146_ns,client147_ns,client148_ns,client149_ns end at 2017年 05月 19日 星期五 11:23:01 CST
