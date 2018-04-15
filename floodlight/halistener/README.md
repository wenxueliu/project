
#HAListenerTypeMarker.java

    public enum HAListenerTypeMarker {
    }

This is a dummy(虚假) marker. IListener enforces call ordering by type. However,
for IHAListeners we only have a single order. So we use this type as a
placeholder(占位符) to satisfy the generic requirement.

简而言之, IListener 是根据类型来排序的, 为了与 IListener 兼容而设计的一个虚假类型.


#IHAListener.java

当 Controller 的角色转变的时候, 监听 IHAListener 的模块会被通知


###注:

floodlight 目前并不支持转换到 standby 模式, 当转换到 standby, floodlight 
将被停止, 客户端应该为即将关闭做准备,比如确保更新操作完全同步

##class IHAListener


###void transitionToActive()

    当 Controller 初始化是 STANDBY, 转换到 Active 的时候, 该函数被调用

###void transitionToStandby()

    使得 Controller 之前是 Active(主动), 现在转换到 Standby(被动)

###void controllerNodeIPsChanged(Map<String, String> curControllerNodeIPs,
                            Map<String, String> addedControllerNodeIPs,
                            Map<String, String> removedControllerNodeIPs);

    Map<String, String> curControllerNodeIPs : controllerId:controllerIP


#LinkDiscoveryManager.java

##class HAListenerDelegate implements IHAListener


###void transitionToActive()

    设置 LinkDiscoveryManager 的 role 为 HARole.ACTIVE
    从存储服务中删除所有的表 controller_link(记录所有Link 信息) 的所有记录
    设置 LinkDiscoveryManager.autoPortFastFeature 的值
    重新启动 link 发现的任务

###void controllerNodeIPsChanged(Map<String, String> curControllerNodeIPs,
            Map<String, String> addedControllerNodeIPs,
            Map<String, String> removedControllerNodeIPs)
    
    什么也不做


###public void transitionToStandby()

    什么也不做
