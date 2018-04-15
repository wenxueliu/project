
Device 可以认为是网络中的虚拟设备, 包含一个或多个 entity;

AttachmentPoint 用于标记一个 Device 中的挂载点.  此外 一个 Device 有多个 AttachmentPoint,
经过这个 AttachmentPoint 可以有多个设备, 需要通过一个对象来标记, 即 entity

entity 可以认为是网络中的主机, 一旦创建就不可以修改(除了它上次看的的时间戳), 包含 mac, ip, vlan, switchDPID, switchPort 等;
其中 switchDPID, switchPort 表名其所属的 AttachmentPoint

EntityClass 用于对不同的 entity 进行标记, IEntityClassifierService 用于划分不同的 entity.

订阅 PACKET_IN, Controller 角色变化, 拓扑变化, EntityClass 分类变化消息

一个线程更新主机, 对每个设备的所有主机执行过期检查. 设备中删除过期的主机
一个线程同步设备, 遍历所有设备, 如果某个设备没有Entity(主机) 存在就删除之

##设备学习

1. 从发送者发送的 arp 包的 srcMac, Vlan srcIpv4(srcIpv6), switch, port 的信息创建 Entity
2. 从代理网关发送的 arp 包的 srcMac, Vlan srcIpv4(srcIpv6), switch, port 的信息创建 Entity
2. 从发送者包的 dstMac, Vlan, dstIpv4(srcIpv6) 的信息创建 Entity.(注:这里没有 switch 和 port 的信息.)
3. 从包的 ip 包的 srcMac, Vlan srcIpv4(srcIpv6), switch, port 的信息创建 Entity

###PACKET_IN

通过 PACKET_IN 的 ARP 包学习网络中的主机.

1. 学习转发 ARP 包的 entity (eth 包头)
2. 学习 ARP 包中的 entity (eth 包体), 并初始化或更新 deviceMap 中的 device, 并通知订阅者设备更新信息.

###当 SLAVE -> MASTER 角色切换

从共享存储取数据之后, 初始化或更新 device, 并通知订阅者.


难点:
   ClassState 的理解, 为什么需要?

###为什么 AttachmentPoint

   一个交换机有多个端口, 每个交换机的每个端口就代表一个入口. 因此 AttachmentPoint
   唯一标记了一个交换机. 当然包括它的生命周期, 如创建时间, 上次更新时间, 过期时间.

###为什么需要 entity

   一个 AttachmentPoint 经过的设备(如主机)有很多, 为了标记经过一个
   AttachmentPoint 的所有设备, 因此需要 entity

###为什么需要 IndexedEntity

   因为有很多 entity, 但一个实体 entity 需要一个唯一标记它的方法, 也许是 MAC,
   也许是 VLAN, 也许是 IP, 当然也可以是多个组合, 因此, IndexedEntity 应需而生

###为什么需要 DeviceUniqueIndex , 即为什么需要 primaryIndex?

    如果前所述, entity 可以理解为唯一标记主机, IndexedEntity 为了按照某种分类方法标记
    一个网络设备. 而 deviceKey 唯一标记一个交换机.  因此, 当找到一个 entity 希望得知
    它所属的设备的且设备只有一个的时候, 可以通过 DeviceUniqueIndex 来标记. 注意这时
    索引为 keyFields 为 MAC, VLAN.

    由于所有设备都存储在 deviceMap 中, 而 deviceMap 以 deviceKey 为 key, 当需要以某些
    字段为索引(比如 VLAN, MAC)时, 这里 DeviceUniqueIndex 建立了与 deviceKey 的对应关系.

###为什么需要 DeviceMultiIndex

    如果前所述, 由于同一的 IndexedEntity(比如当 keyFields 只有 VLAN) 很可能导致有多个设备,
    而 deviceKey 唯一标记一个交换机. 因此, 当找到一个 IndexedEntity 希望得知与它关联的
    所有设备的时候, 这时候就需要 DeviceMultiIndex

###为什么需要 secondaryIndexMap

    由于不同的 keyFields 对应不同的 DeviceMultiIndex, 因此, 需要保存 keyFields
    与 DeviceMultiIndex 的映射关系.

###为什么需要 IEntityClass

    为了标记这些 entity 是属于一个 Device 的, 这些 entity 都有共同的索引且索引的值相同.
    比如以 MAC 和 VLAN 为索引 entity1 和 entity2 虽然 IP 不同, 但是 MAC VLAN 相同, 因此
    entity1 和 entity2 属于同一 IEntityClass

    注意与 IndexedEntity 的区别, IndexedEntity 是为了查询所有 entity 提供的索引.

    此外, IEntityClass 提供了一个自定义查询字段来索引设备的方法.

###为什么需要 IEntityClassifierService

    当有很多 IEntityClass 的时候, 给定一个 entity 我需要指定它属于哪个
    IEntityClass, 此外, 当更新一个 IEntityClass 的 keyFields 时, 我也需要
    通过某种机制来做...

###为什么需要  classStateMap

    了解了 IEntityClass 和 IEntityClassifierService 服务, 知道当存在多个
    IEntityClass 时, 如何维护他们之间的对应关系. 因此需要 classStateMap







ConcurrentHashMap<String, ClassState> classStateMap 维护所有的 IEntityClass 的实体类
DeviceUniqueIndex primaryIndex : 保存了 ((keyFields, entity), deviceKey); DeviceUniqueIndex 类型. 与 deviceMap 关联
deviceMap



DeviceIndex
    　　EnumSet<DeviceField>     keyFields : 所有 IndexedEntity 的 keyFields 共享

    DeviceUniqueIndex
        Map<IndexedEntity, Long> index

        其中
        IndexedEntity
            EnumSet<DeviceField> keyFields,
            Entity entity;


ClassState
    DeviceUniqueIndex classIndex;
    Map<EnumSet<DeviceField>, DeviceIndex> secondaryIndexMap;



IDevice 和 IDeviceListener 是实现了发布和订阅模式

##IDevice

* Long getDeviceKey()
* MacAddress getMACAddress()
* String getMACAddressString()
* VlanVid[] getVlanId()
* IPv4Address[] getIPv4Addresses()
* SwitchPort[] getAttachmentPoints()
* SwitchPort[] getOldAP()
* SwitchPort[] getAttachmentPoints(boolean includeError)
* VlanVid[] getSwitchPortVlanIds(SwitchPort swp)
* Date getLastSeen()
* IEntityClass getEntityClass()

##IDeviceListener

* void deviceAdded(IDevice device)
* void deviceRemoved(IDevice device)
* void deviceMoved(IDevice device)
* void deviceIPV4AddrChanged(IDevice device)
* void deviceVlanChanged(IDevice device)

##Device

    实现了 IDevice 类, 该类的优化空间很大,写代码的人,显然对 java 对象的拷贝和引用语义掌握的非常模糊.

###关键变量

    参见数据结构部分

###Map<DatapathId, AttachmentPoint> getAPMap(List<AttachmentPoint> apList)

    检查 apList 的有效性, 返回有效列表

    遍历 apList，检查是否是 deviceManager 中有效的挂载点，对有效挂载点的列表排序，之后增加到 appMap = Map<DatapathId, AttachmentPoint>(id, ap) 中，
    其中 id 为 ap 所属集群的 id，返回 appMap

    问题： 这里如果 apList 中有多个 AttachmentPoint 属于同一集群或同一交换机, 会导致前面的被后面的冲掉.

###boolean removeExpiredAttachmentPoints(List<AttachmentPoint>apList)

    删除 apList 中过期的挂载点(AttachmentPoints); 如果过期的, 返回true, 否则返回 false; 如何判断过期参见数据结构AttachmentPoint 部分

###List<AttachmentPoint> getDuplicateAttachmentPoints(List<AttachmentPoint>oldAPList, Map<DatapathId, AttachmentPoint>apMap)

    检查 oldAPList 中某个挂载点 id 在 apMap 中存在, 并且比 apMap　中对应的 AttachmentPoint 创建更早, 上次更新最近. 就认为是与 apMap 重复.

    比较 oldAPList 和 apMap 中 id 相同的 AttachmentPoint. 如果前者与后者的 AttachmentPoint 不同,
    且后者的创建时间更晚, 更新时间更早, 而且前者没有过期, 就将前述满足条件对应的前者的集合返回

    遍历 oldAPList 中的元素 ap, 如果 ap 在 apMap 中不存在, 并且没有过期, 创建时间比 apMap 对应的时间晚, 就增加到返回列表中

    问题: 如果 oldAPList 和 apMap 为 null, 返回 null 更合适, 这点关于返回为 empty 还是 null, 整体的代码没有一致性.

###boolean updateAttachmentPoint()

    更新 this.oldAps 为 this.attachmentPoints, 通过 getAPMap 检查 this.attachmentPoints 是否发生移动，如果移动返回 true, 更新 this.attachmentPoints, 否则返回 false

###boolean updateAttachmentPoint(DatapathId sw, OFPort port, Date lastSeen)

    1. 检查新 AttachmentPoint 的有效性, 创建 newAP(sw, port, lastSeen)
    2. 如果 this.oldAps 存在 sw,port 对应的 attachmentPoints, 更新之
    3. 如果 getAPMap(this.attachmentPoints) 本身为 null, 直接增加 newAP;
       如果存在 AP 与 newAP 属于同一挂载点, 且时间比 newAP 旧, 更新之.
       比较 AP 与 newAP, 如果 AP 小于 newAP, AP 加入 this.oldAps, newAP 加入 this.attachmentPoints
                         如果 AP 大于 newAP, newAP 加入 this.oldAps

    TODO: 这里 newAP 与 AP 的比较还存疑

    如果 sw，port 不是有效的挂载点,直接返回 false, 否则, 由 (sw,port,lastSeen) 构造 newAP
    检查 this.oldAps 中是否存在 newAP， 如果存在，从 this.oldAps 中删除之, 更新 this.oldAps, 设置 oldAPFlag = true 并继续
    从 this.attachmentPoints 获取有效的 apMap,
        如果 apMap 为 null,直接增加 newAP, 返回 true. (原因交换机重启, 设备之前存在,现在不存在了)
        如果不为 null, 如果 apMap 中不存在 newAp ,直接增加 newAp, 更新AttachmentPoint,  返回true
                      如果 apMap 中存在 oldAp 与 newAP 的 ID 相同 并且 oldAP.equals(newAP) 相同, 设置时间, 返回 false
                      否则, 调用 x = deviceManager.apComparator.compare(oldAP, newAP)  
                            如果 x < 0, oldAP 增加到 this.oldAps, newAP 增加到 this.attachmentPoints, 
                                如果 topology.isInSameBroadcastDomain(oldAP, newAP) == flase, 返回 ture
                                否则继续
                            如果 x >=0 且 oldAPFlag = true ,  认为 newAP 与 oldAP 重复, 将 newAP 增加到 this.oldAps.
    返回 false

    问题, 重复new 了很多不必要的对象

         Device 下的 AttachmentPoint 的 topology.getL2DomainId(ap.getsw()) 必须不一样, 否则,这里存在问题.

         为什么要 getAPMap ?


###boolean deleteAttachmentPoint(DatapathId sw, OFPort port)

    检查 this.oldAPs 中 是否存在对应的 sw,port，如果存在，就更新 this.oldAPs
    检查 this.AttachmentPoint 中是否存在对应的 sw,port，如果存在，就更新 this.AttachmentPoint， 返回 True，否则返回 False

###boolean deleteAttachmentPoint(DatapathId sw)

    检查 this.oldAPs 中是否存在 sw，如果存在，就从 this.oldAPs 中删除与 sw 相关的 AttachmentPoint
    检查 this.AttachmentPoint 中 是否存在 sw，如果存在，就从 this.AttachmentPoint 删除与 sw 相关的 AttachmentPoint， 返回 True，否则返回 False

### SwitchPort[] getOldAP()

    获取没有 Expire 的 oldAPs

    问题: if (oldAPList != null) 改为 if(!oldAPList.isEmpty()) 更合适

###SwitchPort[] getAttachmentPoints(boolean includeError)

    遍历 this.AttachmentPoint:
    如果 includeError 为 flase, 直接返回 this.AttachmentPoint 的 SwitchPort[] 形式
    否则, 检查 oldAPs 和 getAPMap(this.AttachmentPoint) 重复的部分，以数组形式返回 this.AttachmentPoint 加 重复部分

###SwitchPort[] getAttachmentPoints()

    返回 getAttachmentPoints(false)

###IPv4Address[] getIPv4Addresses()

　　找到 this.entities 关联的所有设备 Device,  TODO
    WHY?????

    遍历 this.entities 每个元素 e, 从 deviceManager 找是否其他设备存在相同的 IP, 如果不存在, 就加入返回队列.

    devices = deviceManager.queryClassByEntity(entityClass, ipv4Fields, e)
    对于 devices 每个元素 d，  d.getDeviceKey() != deviceKey 并且 d.entities 的存在元素 se，
    e.getIpv4Address = se.getIpv4Address && se.getLastSeenTimestamp().compareTo(e.getLastSeenTimestamp() > 0 ,说明 ip 重复了.

###IPv6Address[] getIPv6Addresses() {

    与 getIPv4Addresses 思路完全相同, 只是这里是 ipv6


###VlanVid[] getSwitchPortVlanIds(SwitchPort swp)

    从 this.entities 中找到 swp 对应的 entities 的 vlanid 的集合

    遍历 this.entities 每个元素 e, 返回 e.switchDPID 和 e.switchPort 与 swp 匹配的 vlan 的集合

###Date getLastSeen()

    this.entities 距现在时间最近的 e.getLastSeenTimestamp()

###VlanVid[] getVlanId()

    调用 computeVlandIds()

###VlanVid[] computeVlandIds() {

    this.entities 所有 vlan 的并集

###int entityIndex(Entity entity) {

    entity 在 this.entities 中的索引

以下方法说明略
###Long getDeviceKey()
###MacAddress getMACAddress()
###String getMACAddressString()


##IEntityClass

如果两个设备的 IEntityClass 的 keyFields 相同就认为是同一 device

一系列　IEntityClass　组成 Device, IEntityClass 基于 key 来比较, 如果 两个 IEntityClass 的交集相等,
那么 这两个 IEntityClass 属于同一 Device

目前实现该接口的是 DefaultEntityClassifier.DefaultEntityClass

* EnumSet<DeviceField> getKeyFields()
* String getName()


##IEntityClassifierService

IEntityClassifierService 和 IEntityClassListener 实现了 发布-订阅者模式

对 IEntityClass 的划分, 遵守传递性, 比如 x, y 属于 class c, x, z 属于 class c, 那么 y,z 属于 class c.

* IEntityClass classifyEntity(Entity entity)
* EnumSet<DeviceField> getKeyFields()
* IEntityClass reclassifyEntity(IDevice curDevice, Entity entity)
* void deviceUpdate(IDevice oldDevice, Collection<? extends IDevice> newDevices)
* void addListener(IEntityClassListener listener)

##IEntityClassListener

* void entityClassChanged(Set<String> entityClassNames)


##DefaultEntityClassifier

    实现了 IEntityClassifierService, 是 keyFields 和 DefaultEntityClass 的组合.
    keyFields 为 MAC+VLAN

###关键变量

    EnumSet<DeviceField> keyFields 初始化包含　MAC VLAN
    DefaultEntityClass entityClass　:　new DefaultEntityClass("DefaultEntityClass")

###IEntityClass classifyEntity(Entity entity)

    返回　entityClass， 与参数 entity 无关

###IEntityClass reclassifyEntity(IDevice curDevice, Entity entity)

    返回　entityClass， 与参数 curDevice, entity 无关

###EnumSet<DeviceField> getKeyFields()

    返回　keyFields

###deviceUpdate(IDevice oldDevice, Collection<? extends IDevice> newDevices)

    什么也不做

###void addListener(IEntityClassListener listener)

    什么也不做


##DefaultEntityClass

    DefaultEntityClassifier　的内部类, 实现了 IEntityClass

###关键变量

    name : 实体名称

###EnumSet<IDeviceService.DeviceField> getKeyFields()

    返回 DefaultEntityClassifier 的变量 keyFields

###String getName()

    返回 


##IDeviceService

###关键变量

    String CONTEXT_SRC_DEVICE = "net.floodlightcontroller.devicemanager.srcDevice"
    String CONTEXT_DST_DEVICE = "net.floodlightcontroller.devicemanager.dstDevice"
    String CONTEXT_ORIG_DST_DEVICE = "net.floodlightcontroller.devicemanager.origDstDevice"
    FloodlightContextStore<IDevice> fcStore = new FloodlightContextStore<IDevice>();


* IDevice getDevice(Long deviceKey)
* IDevice findDevice(MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address, DatapathId switchDPID,OFPort switchPort)
IDevice findClassDevice(IEntityClass entityClass,MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address)
* Collection<? extends IDevice> getAllDevices()
* void addIndex(boolean perClass,EnumSet<DeviceField> keyFields)
* Iterator<? extends IDevice> queryDevices(MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address,DatapathId switchDPID,OFPort switchPort)
* Iterator<? extends IDevice> queryClassDevices(IEntityClass entityClass,MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address, DatapathId switchDPID,OFPort switchPort)
* void addListener(IDeviceListener listener)
* void addSuppressAPs(DatapathId swId, OFPort port)
* void removeSuppressAPs(DatapathId swId, OFPort port)
* Set<SwitchPort> getSuppressAPs()


#数据结构

##enum DeviceField

    MAC, IPV4, VLAN, SWITCH, PORT

##SwitchPort

    交换机:端口映射类

    DatapathId switchDPID  : 交换机 ID
    OFPort port            : 交换端口
    ErrorStatus errorStatus: 错误状态

##AttachmentPoint

    设备的挂载点, 一个设备可以有多个挂载点. 这里最直观的理解就是交换机与其上一个端口组成一个挂载点.

    DatapathId   sw
    OFPort       port
    Date         activeSince
    Date         lastSeen

##Entity

    网络中的实体, 实体依赖 AttachmentPoint. 每个 AttachmentPoint 可以包含多个 Entity.
    比如一个 AttachmentPoint (交换机的某一个端口)可能有多个主机的数据包通过, 那么一个
    Entity 就记录了 AttachmentPoint 经过的一个主机.

    实体(Entity)是可以比较的, 在设备(Device)中是按照顺序排序的, 比较的依据依次为
    macAddress, switchDPID, switchPort, ipv4Address, IPv6Address, vlan

    MacAddress     macAddress
    IPv4Address    ipv4Address
    IPv6Address    ipv6Address;
    VlanVid        vlan
    DatapathId     switchDPID  : 所属交换机的 DPID
    OFPort         switchPort  : 所属交换机的端口
    Date           lastSeenTimestamp : 实体在网络中上次观察到的时间
    Date           activeSince       : 实体创建时间
    int ACTIVITY_TIMEOUT = 30000  ms : 激活的超时时间
    lastSeenTimestamp - activeSince > ACTIVITY_TIMEOUT 之后, activeSince 才可变 lastSeenTimestamp

    只有 lastSeenTimestamp 是可变的, 其他一旦创建便不可变



##Device

    实现了 IDevice 类

Device 可以认为是网络中的交换机, 包含一个或多个 entity; entity 可以认为是网络中的主机, 一旦创建
就不可以修改(除了它上次看的的时间戳), 一个 entity 是一个网络中实体, 包含 ip, MAC, vlan等; AttachmentPoint
用于标记一个 Device 中的挂载点,来源与 entity, 可以认为一个 Device 中的 entity 与 AttachmentPoint
是一一对应的. 在一个 Device 中的实体(entities)是排序的

    Long                     deviceKey        : 设备的主键,用于唯一标记一台 Device
    DeviceManagerImpl        deviceManager    : 该设备的管理者
    Entity[]                 entities         : 设备中所有挂载点的所有 entity 的集合
    IEntityClass             entityClass      : 待定
    String                   macAddressString : this.entities[0].getMacAddress().toString()
    VlanVid[]                vlanIds          : 主机中的所有 VlanId 的列表
    String                   dhcpClientName   :
    List<AttachmentPoint>    oldAPs           : 被更新了但还没有过期的 attachmentPoints
    List<AttachmentPoint>    attachmentPoints : 主机中所有 (sw,port) 的列表

    一些原则：update的时候，对于 attachmentPoints 一定要调用 getAPMap 检查有效性

##设备相关信息

##DeviceIndex

关键变量

    EnumSet<DeviceField> keyFields; 该类中所有的　entity 都共享　keyFields

* abstract Iterator<Long> queryByEntity(Entity entity)
* abstract Iterator<Long> getAll()
* abstract boolean updateIndex(Device device, Long deviceKey)
* abstract boolean updateIndex(Entity entity, Long deviceKey)
* abstract void removeEntity(Entity entity)
* abstract void removeEntity(Entity entity, Long deviceKey)

###void removeEntityIfNeeded(Entity entity, Long deviceKey,Collection<Entity> others)

    ie = IndexedEntity(this.keyFields, entity)
    1. ie 不存在与 others 中
    2. deviceKey 在  this.index.get(ie)中，删除之（只第一个满足条件的）

##IndexedEntity

    包装 entity, 增加 keyFields,  DeviceUniqueIndex 的辅助类

    原因是标记更好标记一个 entity. 比如, A 希望 entity 以 MAC, IP 来唯一
    标记, B 希望 entity 以 MAC, IP, VLAN 标记.

    hashCode 和 equals 都是对 keyFields 比较的.

###关键变量

    EnumSet<DeviceField> keyFields
    Entity entity

###boolean hasNonNullKeys()

    keyFields　包含　MAC 返回 true
               包含 IPV4　或 SWITCH　或　PORT　或　VLAN 中对应的　entity 不为　null

##DeviceUniqueIndex

    实现 DeviceIndex; 保存了 entity 与 deviceKey 的映射关系, 这里 entity 与 deviceKey 的关系是一一对应

    如果前所述, entity 可以理解为唯一标记一个交换机和它的端口(sw,port), 而
    deviceKey 唯一标记一个交换机. 因此, 当找到一个 entity 希望得知它所属
    的设备的时候, 必须通过 DeviceUniqueIndex 来标记.

    index 保存了所有的 entity 与 deviceKey 的映射关系. 引入 IndexedEntity
    的原因为了标记更好标记一个 entity. 比如, A 希望 entity 以 MAC, IP 来唯一
    标记, B 希望 entity 以 MAC, IP, VLAN 标记.

###关键变量

    EnumSet<DeviceField> keyFields  : 该类中所有的 entity 都共享　keyFields
    ConcurrentHashMap<IndexedEntity, Long> index : 保存 ((entity,keyFields),　deviceKey) 的映射关系

###Long findByEntity(Entity entity)

    返回 this.index 中 entity 对应的 deviceKey

###Iterator<Long> queryByEntity(Entity entity)

    返回 this.index 中 entity 对应的 deviceKey 的迭代器

###Iterator<Long> getAll()

    返回 this.index 中所有 entity 的迭代器

###boolean updateIndex(Device device, Long deviceKey)

    遍历 device.entities 的每一个元素 entity, 将 entity, deviceKey 加入 this.index

###boolean updateIndex(Entity entity, Long deviceKey)

    将 entity,deviceKey 加入 index

###void removeEntity(Entity entity)

    从 index 中删除 entity

###void removeEntity(Entity entity, Long deviceKey)

    从 index 中 删除 value 为 deviceKey 的 entity

###void removeEntityIfNeeded(Entity entity, Long deviceKey,Collection<Entity> others)

    ie = IndexedEntity(this.keyFields, entity)
    1. 如果 entity 在 other 中, 直接返回
    2. deviceKey 在 this.index.get(ie)中，删除之（只第一个满足条件的）


##DeviceMultiIndex

    实现　DeviceIndex; 保存了 entity 与 deviceKey 的映射关系, 这里 entity 与 deviceKey 的关系是一对多对应
    应用于 secondaryIndexMap 变量中

###关键变量

    EnumSet<DeviceField> keyFields : 该类中所有的　entity 都共享　keyFields
    ConcurrentHashMap<IndexedEntity, Collection<Long>> index ： IndexedEntity<deviceKey, entity>:Collecton<devicesKey>

### Iterator<Long> queryByEntity(Entity entity)

    ie = IndexedEntity(this.keyFields, index)
    ie 是否存在于 this.index 中 ,如果存在，返回 index.get(ie).iterator，否则返回空迭代器

### Iterator<Long> getAll()

    返回 this.index.values().iterator()

### boolean updateIndex(Entity entity, Long deviceKey)

    将 this.index.putIfAbsent(IndexedEntity(keyFields, entity)).add(deviceKey)

### boolean updateIndex(Device device, Long deviceKey)

    遍历 device.entities, 调用 updateIndex(Entity entity, Long deviceKey)

### void removeEntity(Entity entity)

    从 this.index 中删除 entity

###void removeEntity(Entity entity, Long deviceKey)

    从 this.index 的 key 为 entity 中删除 deviceKey

###void removeEntityIfNeeded(Entity entity, Long deviceKey,Collection<Entity> others)

    ie = IndexedEntity(this.keyFields, entity)
    1. ie 不存在与 others 中
    2. 在 this.index.get(ie) 中删除对应的 deviceKey（只删除第一个满足条件的）

##SyncEntity

    DeviceSyncRepresentation 内部类

###关键变量

    long macAddress
    int ipv4Address
    short vlan
    long switchDPID
    short switchPort
    Data lastSeenTimestamp

###Entity asEntity()

    将 SyncEntity 转化为 Entity

###compareTo(SyncEntity other)

    比较 lastSeenTimestamp 

###DeviceSyncRepresentation

###关键变量

    String key
    List<SyncEntity> entities //根据 lastSeenTimestamp 排序, 保存 device 中的 entity

###DeviceSyncRepresentation(Device device)

    device 中的 entity
    1. entity.hasSwitchPort() 为 false
    2. entity 在 device 的 attachmentPoint 中
    3. entity 的 ip 不为 null
    如果上面三个条件有一个满足, 就增加到 entities

###boolean isAttachmentPointEntity(SwitchPort[] aps, Entity e)

    e 的 sw, port 在 aps 中 返回 true 

###String computeKey(Device d)

    返回 EntityClass[::MAC][::VLAN][::SWITCH][::IPV4], [] 内表示表示如果不存在就忽略

以下方法说明略

* String getKey()
* void setKey(String key)
* List<SyncEntity> getEntities()
* void setEntities(List<SyncEntity> entities)

###DeviceIndexInterator

    设备的迭代器

###关键变量

    DeviceManagerImpl deviceManager : 设备管理
    Iterator<Long> subIterator  : 迭代器

方法说明略
* boolean hasNext()
* Device next()
* void remove()

##FilterIterator

    实现迭代器

###关键变量

    Iterator<T> subIterator : 迭代器
    T next  : 下一个元素

方法说明略
* boolean hasNext()
* Device next()
* void remove()

##DeviceIterator

    继承 FilterIterator

###关键变量

    Iterator<T> subIterator : 迭代器
    T next  : 下一个元素
    IEntityClass[] entityClasses
    MacAddress macAddress
    VlanVid vlan
    IPv4Address ipv4Address
    DatapathId switchDPID
    OFPort switchPort

###boolean matches(Device value)

    1. 如果 entityClasses 不为 null, value.getEntityClass() 必须存在于 entityClasses 中 
    2. 如果 macAddress 不为 null, 必须与 value.getMACAddress() 相同
    3. 如果 vlan 不为 null,  value.getVlanId() 必须包含 vlan
    4. 如果 ipv4Address 不为 null, value.getIPv4Addresses() 必须包含 ipv4Address
    5. 如果 switchDPID 或  switchPort, value.getAttachmentPoints() 必须包含 switchDPID 或 switchPort
    只有同时满足以上 5 个条件才返回 true


##DefaultEntityClassifier

    根据 entity 来对 IEntityClass 分类

    static EnumSet<DeviceField> keyFields = EnumSet.of(DeviceField.MAC, DeviceField.VLAN)
    static DefaultEntityClass entityClass = new DefaultEntityClass("DefaultEntityClass")

###IEntityClass reclassifyEntity(IDevice curDevice, Entity entity)

    返回 this.entityClass

###IEntityClass classifyEntity(Entity entity)

    返回 this.entityClass

###void deviceUpdate(IDevice oldDevice, Collection<? extends IDevice> newDevices) 

    no-op

###EnumSet<DeviceField> getKeyFields()

    返回 this.keyFields

### void addListener(IEntityClassListener listener)

    no-op

###class DefaultEntityClass

    String name

    EnumSet<IDeviceService.DeviceField> getKeyFields() 与 DefaultEntityClassifier.getKeyFields() 相同
    String getName()  返回 name


##核心实现

##ClassState

    DeviceManagerImpl 的内部类,缓存 EntityClass 的状态, 注意其与 DeviceUniqueIndex 和 DeviceMultiIndex 的关系

    与 classStateMap 变量相关联

    目前实现中 keyFields 为 DefaultEntityClass.getKeyFields(), classIndex 为
    null, secondaryIndexMap 为 [IPv4 : DeviceMultiIndex(IPv4)] [IPv6 : DeviceMultiIndex[IPv6]]

    classStateMap 为 DefaultEntityClass.getName() : ClassState(DefaultEntityClass)

###关键变量

    DeviceUniqueIndex classIndex : 见构造函数说明  DeviceUniqueIndex(class.getKeyFields())

    Map<EnumSet<DeviceField>, DeviceIndex> secondaryIndexMap : 见构造函数说明


###ClassState(IEntityClass clazz)

    初始化 classIndex 和 secondaryIndexMap

    如果 clazz.getKeyFields() 与 entityClassifier.getKeyFields()(DefaultEntityClassifier.getKeyFields()) 不等, 就初始化 classIndex 为 DeviceUniqueIndex(clazz.getKeyFields()). 否则为 null

    遍历 this.perClassIndices 每个元素 fields, 保持到 secondaryIndexMap 中 (fields, new DeviceMultiIndex(fields))

    因此, 当 clazz.getKeyFields() 与 entityClassifier.getKeyFields() 相同, classIndex = null, secondaryIndexMap 在所有情况下都是一样的
    因此, 当 clazz.getKeyFields() 与 entityClassifier.getKeyFields() 不同, classIndex = DeviceUniqueIndex, secondaryIndexMap 在所有情况下都是一样的


问题: 为什么需要 ClassState, 为了对不同的 IEntityClass 进行不同的保持

##DeviceSyncManager

    设备同步管理

    只有 Master 角色才可以操作共享存储(集群所有节点共享)

###关键变量

    ConcurrentMap<Long, Long> lastWriteTimes lastWriteTimes : (d.getDeviceKey(), now) 保存 device 上次更新时间

###void storeDevice(Device d)

    调用 writeUpdatedDeviceToStorage(d) 将 device 对应的字段写入共享存储, 等待同步
    更新 lastWriteTimes 中 d 对应字段的时间为 now

###void writeUpdatedDeviceToStorage(Device device)

    将 device 对应的字段写入共享存储, 等待同步

###void storeDeviceThrottled(Device d)

    如果该设备上次更新时间到现在超过 5min 就调用 storeDevice() 并更新
    lastWriteTimes; 否则什么也不做

###void removeDevice(Device d)

    从 lastWriteTimes 和 同步存储中删除 d 对应的字段

###void removeDevice(Versioned<DeviceSyncRepresentation> dev)

    从共享存储删除 dev 版本为 dev.getVersion(), dev.getKey() 对应的指定版本

###void goToMaster()

    遍历共享存储中的所有的设备的所有 entitys, 调用 learnDeviceByEntity(se.asEntity()) 学习该设备是否可用
    启动 storeConsolidateTask 任务

###void consolidateStore()

    在 SLAVE->MASTER 转换或 MASTER 模式, 遍历所有设备, 如果不能 deviceMap 或 entity 找到该设备, 就从共享存储删除该设备

    对 storeClient 的每一个 storedDevice, 对 storedDevice 中 entity 调用 findDevice() 寻找 entity 是否存在对应的设备,
    如果某个 entity 存在对应 Device (entity 存在与 primaryIndex 中), 就删除 storedDevice.




##DeviceUpdate

    DeviceManagerImpl 的内部类, 维护设备改变的状态

###关键变量

    Device device : 设备对象
    Change change : 对设备的改变,包括 ADD, DELETE, CHANGE
    EnumSet<DeviceField> fieldsChanged : 对设备改变的 fields


##AttachmentPointComparator

    DeviceManagerImpl 的内部类, 比较 AttachmentPoint, 假设 参与比较的 attachmentPoints 在同一 L2 Domain

###int compare(AttachmentPoint oldAP, AttachmentPoint newAP)

    比较 AttachePoint 的 dataPathId, port, L2DomainId, isBroadcastDomainPort
    优先级:
        dataPath : 转换 Long 类型比大小
        port: 其他小于 OFPort.LOCAL
        activeSince : 如果 oldAP 迟于 newAP, 那么返回 -compare(newAP, oldAP), 即反序排列
        比较 lastSeen


##DeviceManagerImpl

###关键变量

    依赖其他模块
    IFloodlightProviderService floodlightProvider
    ITopologyService topology
    IStorageSourceService storageSource
    IRestApiService restApi
    IThreadPoolService threadPool

    ISyncService syncService
    IStoreClient<String, DeviceSyncRepresentation> storeClient : syncService.getStoreClient()
    DeviceSyncManager deviceSyncManager
    HAListenerDelegate haListenerDelegate
    IEntityClassifierService entityClassifier  : 目前由 DefaultEntityClassifier 实现(非完全实现)
    DeviceUniqueIndex primaryIndex : 存放 entityClassifier.getKeyFields()

    调试相关
    IDebugEventService debugEventService
    IEventCategory<DeviceEvent> debugEventCategory
    IDebugCounterService debugCounters

    常量
    String DEVICE_SYNC_STORE_NAME = DeviceManagerImpl.class.getCanonicalName() + ".stateStore"
    //同步设备的信息到存储服务的间隔 5 min
    int DEFAULT_SYNC_STORE_WRITE_INTERVAL_MS = 5*60*1000
    int syncStoreWriteIntervalMs = DEFAULT_SYNC_STORE_WRITE_INTERVAL_MS

    //初始化同步存储
    DEFAULT_INITIAL_SYNC_STORE_CONSOLIDATE_MS = 15*1000
    initialSyncStoreConsolidateMs = DEFAULT_INITIAL_SYNC_STORE_CONSOLIDATE_MS

    //默认同步存储
    int DEFAULT_SYNC_STORE_CONSOLIDATE_INTERVAL_MS = 75*60*1000
    int syncStoreConsolidateIntervalMs = DEFAULT_SYNC_STORE_CONSOLIDATE_INTERVAL_MS

    //主机过期时间 60 min
    int ENTITY_TIMEOUT = 60*60*1000
    //主机清理时间 60 min
    int ENTITY_CLEANUP_INTERVAL = 60*60


    //内部类
    AttachmentPointComparator apComparator : AttachmentPointComparator 实例

    Set<SwitchPort> suppressAPs : 屏蔽的 AttachmentPoint, 由 addSuppressAPs(DatapathId swId, OFPort port) , removeSuppressAPs(DatapathId swId, OFPort port), getSuppressAPs() 改变

    ConcurrentHashMap<Long, Device> deviceMap  :  dataPathId 与 Device 的映射
    AtomicLong deviceKeyCounter = new AtomicLong(0) : 设备的 key, 这里对于确保唯一;


    ListenerDispatcher<String,IDeviceListener> deviceListeners: 设备订阅者, 由 addListener() 改变
    ConcurrentHashMap<String, ClassState> classStateMap; 其中 IEntityClass.getName(): ClassState(IEntityClass), 这里 IEntityClass 为 device.getEntityClass() 即 DefaultEntityClass

    IEntityClassifierService entityClassifier : DefaultEntityClassifier 类, 保存了 keyFields, entityClass

    DeviceUniqueIndex primaryIndex : 保存了 ((entityClassifier.getKeyFields(), entity), deviceKey); DeviceUniqueIndex 类型. 与 deviceMap 关联

    HashMap<EnumSet<DeviceField>, DeviceMultiIndex> secondaryIndexMap : 存放非共享的所有 keyFields, 由 addIndex() 和 getClassState() 修改, 目前没有任何元素

    Set<EnumSet<DeviceField>> perClassIndices : 存放每个类的公共 keyField. 默认包含 DeviceField.IPV4, DeviceField.IPV6, 由 addIndex(true, keyFields) 改变

    ConcurrentHashMap<String, ClassState> classStateMap  :  存放, IEntityClass.getName() : ClassState(IEntityClass) 映射关系;　由 getClassState 改变. 目前只有 DefaultEntityClass.getName() : ClassState(DefaultEntityClassifier)

    //线程相关
    SingletonTask entityCleanupTask : entity(主机) 清除线程, 删除过期网络主机
    SingletonTask storeConsolidateTask : 待定

###IDevice getDevice(Long deviceKey)

    deviceMap.get(deviceKey)

###IDevice findDevice(MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address, DatapathId switchDPID,OFPort switchPort)

    由 MacAddress macAddress, VlanVid vlan,IPv4Address ipv4Address, DatapathId switchDPID,OFPort switchPort 构造 Entity 对象, 调用 findDeviceByEntity(Entity) 返回设备

    注意: 分析此函数, 确保理清 DefaultEntityClassifier 与 DefaultEntityClass 和 ClassState 的关系
    DefaultEntityClassifier 包含 DefaultEntityClass 和 keyFields(VLAN MAC)
    DefaultEntityClass.getKeyFields() 就是 DefaultEntityClassifier.getKeyFields()
    ClassState 需要 IEntityClass 来构造, 但是利用了 IEntityClass.getKeyFields(), 当 IEntityClass 是 DefaultEntityClassifier 时,  ClassState.classIndex = null, 如果不是 DefaultEntityClassifier 时, ClassState.classIndex 为 DeviceUniqueIndex(IEntityClass.getKeyFields())

###boolean allKeyFieldsPresent(Entity e, EnumSet<DeviceField> keyFields)

    如果 keyFields 中如果存在 IP SWITCH PORT 任一或全部, 且 e 对应的 IP SWITCH PORT 不为 null 时, 返回true.

###Device findDeviceByEntity(Entity entity)

    查询是否在 primaryIndex 的 index 数据成员中,
        如果存在,直接返回,
        如果不存在, 返回 null

    注: 目前的实现, 这主要是 entityClassifier 是 DefaultEntityClassifier
        entityClassifier.classifyEntity(entity) 与 entity 无关, 是 DefaultEntityClass("DefaultEntityClass")
        classState.classIndex  在此种情况下为 null
        因此 findDeviceByEntity 完全由 primaryIndex 来决定

###Device findDestByEntity(IEntityClass reference, Entity dstEntity)

    如果 primaryIndex 中找 dstEntity 到对应的 deviceKey, 返回  deviceMap.get(deviceKey)
    否则从 classStateMap.get(dstEntity.getName()).classIndex 中找 dstEntity 对应 deviceKey, 返回 deviceKey(当不为null)对应的 deviceMap.get(deviceKey)

    主: 目前官方只实现了 DefaultEntityClass. 如果没有自定义, 一般认为完全由 primaryIndex 决定

###IDevice findClassDevice(IEntityClass entityClass, MacAddress macAddress, VlanVid vlan, IPv4Address ipv4Address)

    调用 allKeyFieldsPresent 校验参数, 调用 findDestByEntity(entityClass, e)

###Collection<? extends IDevice> getAllDevices()

    返回 deviceMap.values()

###void addIndex(boolean perClass,EnumSet<DeviceField> keyFields)

    如果 perClass 为 true, 增加到 perClassIndices
    否则增加到 secondaryIndexMap

###public Iterator<? extends IDevice> queryDevices(MacAddress macAddress,VlanVid vlan,IPv4Address ipv4Address,DatapathId switchDPID, OFPort switchPort)

    获取 secondaryIndexMap 或 deviceMap.values() 的迭代器

    DeviceIndex index
    Iterator<Device> deviceIterator : 设备迭代器

    当 macAddress, vlan, ipv4Address,switchDPID, switchPort 组成的 EnumSet<DeviceField> 不存在或size() == 0
时 deviceIterator = deviceMap.values().iterator()
    否则  deviceIterator = DeviceIndexInterator(this, index.queryByEntity(entity)) 
    返回 DeviceIterator(deviceIterator, null, macAddress, vlan, ipv4Address, switchDPID, switchPort)

###Iterator<? extends IDevice> queryClassDevices(IEntityClass entityClass,MacAddress macAddress,VlanVid vlan,IPv4Address ipv4Address,DatapathId switchDPID,OFPort switchPort)

    从 ClassState.secondaryIndexMap 获取, 如果不行, 从 ClassState.classIndex 获取, 如果不行, 从 deviceMap 获取

    具体:
    由 (macAddress,vlan, ipv4Address,switchDPID, switchPort) 构成的 EnmuSet 在 perClassIndices 中, 将 DeviceIndexInterator() 加入迭代器iterator, 返回 MultiIterator<Device>(.iterator.iterator())

    如果 entityClass.keyFields 等于 entityClassifier.keyFields 并且 由(macAddress,vlan, ipv4Address,switchDPID, switchPort)构成的 EnmuSet 不在 perClassIndices 中, 返回 DeviceIterator(deviceMap.values().iterator(),new IEntityClass[] { entityClass },macAddress, vlan, ipv4Address,switchDPID, switchPort) 

    如果 entityClass.keyFields 不等于 entityClassifier.keyFields 并且 由(macAddress,vlan, ipv4Address,switchDPID, switchPort)构成的 EnmuSet 不在 perClassIndices 中, 返回 DeviceIndexInterator()

###Iterator<Device> getDeviceIteratorForQuery(MacAddress macAddress,VlanVid vlan,IPv4Address ipv4Address,DatapathId switchDPID,OFPort switchPort)

    如果由(macAddress,vlan, ipv4Address,switchDPID, switchPort)构成的 EnmuSet 不在 perClassIndices 中 返回 deviceMap.values().iterator()

    否则 DeviceIterator(DeviceIndexInterator(this, index.queryByEntity(entity)), null, macAddress,vlan,ipv4Address,switchDPID,switchPort)

###void addListener(IDeviceListener listener)

    listener 增加到 deviceListeners 中

###void addSuppressAPs(DatapathId swId, OFPort port)

    SwitchPort(swId, port) 增加到 suppressAPs 中

###void removeSuppressAPs(DatapathId swId, OFPort port)

    suppressAPs 中删除 SwitchPort(swId, port)

###Set<SwitchPort> getSuppressAPs()

    获取 suppressAPs

###boolean isValidAttachmentPoint(DatapathId switchDPID,OFPort switchPort)

    当 switchDPID, switchPort 不是 topology 的挂载点, 或是 suppressAPs 的元素时, 返回 false

###Iterator<Device> queryClassByEntity(IEntityClass clazz,EnumSet<DeviceField> keyFields,Entity entity)

    返回　DeviceIndexInterator(this, getClassState(clazz)secondaryIndexMap.get(keyFields).queryByEntity(entity)) 实际是　DeviceIndexInterator(this, DeviceMultiIndex(keyFields)．queryByEntity(entity))

###void deleteDevice(Device device)

    1. 调用 removeEntity(entity, device.getEntityClass(),device.getDeviceKey(), emptyToKeep, new ArrayList<Entity>())
    2. deviceMap 中删除　device

###void removeEntity(Entity removed,IEntityClass entityClass,Long deviceKey,Collection<Entity> others

    primaryIndex, secondaryIndexMap, classState.secondaryIndexMap(), classState.classIndex 中删除 removed,deviceKey,others)

以下方法说明略

* void setSyncServiceIfNotSet(ISyncService syncService)
* IHAListener getHAListener()
* void setInitialSyncStoreConsolidateMs(int intervalMs)
* void setSyncStoreWriteInterval(int intervalMs)
* void scheduleConsolidateStoreNow()
* Device allocateDevice(Long deviceKey,Entity entity,IEntityClass entityClass)
* Device allocateDevice(Long deviceKey,String dhcpClientName,List<AttachmentPoint> aps,List<AttachmentPoint> trueAPs,Collection<Entity> entities,IEntityClass entityClass) 
* Device allocateDevice(Device device,Entity entity,int insertionpoint)
* Device allocateDevice(Device device, Set <Entity> entities)
* EnumSet<DeviceField> getEntityKeys(MacAddress macAddress,VlanVid vlan,IPv4Address ipv4Address,DatapathId switchDPID,OFPort switchPort) : 为了获取一个 entity 的索引

##IEntityClassListener 实现

###void entityClassChanged (Set<String> entityClassNames)

如果 deviceMap 中的所有 Device d, 如果 d.getEntityClass() == null 或 d 存在于 entityClassNames 中, 
调用 reclassifyDevice(d) 重新对设备分类 

####boolean reclassifyDevice(Device device) 
    
    entityClass = entityClassifier.classifyEntity(entity)
        
    如果 device.getEntityClass() 为 null 
    或 entityClass 为 null 
    或 entityClass.getName() 等于 device.getEntityClass().getName() 就认为需要重新分类, 于是
    1. 调用  deleteDevice(device) 从 deviceMap 删除 device,  secondaryIndexMap 和 classState.secondaryIndexMap(实际为 perClassIndices) 中删除 device 中的 entity
    2. 调用 processUpdates(DeviceUpdate(device,DeviceUpdate.Change.DELETE, null)) 更新设备, 
    3. 对 device 的每个 entity 调用 learnDeviceByEntity(entity) 学习设备, 之后返回 true

    否则返回 false


##ITopologyListener 实现

###void topologyChanged(List<LDUpdate> updateList)

    遍历所有设备, 如果某个设备的挂载点被更新, 就调用 sendDeviceMovedNotification(d) 发送修改通知

###void sendDeviceMovedNotification(Device d)

    将 d 存入 storeClient, 重置设备修改时间
    所有订阅 deviceListeners 的订阅者调用 deviceMoved(d)



##实体清除线程

    模块一旦启动, 每隔一小时进行一次设备更新操作

###void cleanupEntities ()

    过期时间 60 min

    toRemove 保存过期的 entity
    toKeep 保存没有过期的 entity
    遍历每一台 Device(交换机)
        遍历每一台 Device(交换机)的 entity
                如果 entity 过期加入就 toRemove, 没有过期就加入 toKeep，
                如果 toRemove 为 NULL， 表明没有 Entity 过期, 返回继续检查下一台设备
                如果 toRemove 不为 NULL, 调用 void removeEntity() 删除 toRemove 中的 entity
                如果 toKeep 为 NULL， 表明该台设备的全部 entities 都过期，
                    DeviceUpdate update = new DeviceUpdate(d, DELETE, null);
                    deviceUpdates.add(update)
                如果 toKeep 不为 NULL
                    for e : toRemove  removeEntity(e, d.getEntityClass(), d.getDeviceKey(), toKeep)
                    用 toKeep 构造 newDevice，检查改变的 Field，如果改变的 Field 不为 0， 调用

                        update = new DeviceUpdate(d, CHANGE, changedFields);
                        deviceUpdates.add(update);

          最后调用 processUpdates(deviceUpdates);

    并发删除, 如果已经为 null, 那么,

### EnumSet<DeviceField> findChangedFields(Device device,Entity newEntity) 

    changedFields 保持 ip, vlan, switch
    如果 newEntity 中的 ip, vlan, switch(sw,port) 与 device 某一 entity 的某一 fields 相同, 从 changedFields 删除该 field
    如果 newEntity 中的 ip, vlan, switch(sw,port) 有任一为 null, 从 changedFields 删除该 field

    即找到存在于 newEntity 中, 不存在与 device 中任一 entity 中 field

    注意: 是否存在, device 的其中一个 entity1.getVlan() 与 newEntity.getVlan() 相同, 另一 entity2.getIp()
    与 newEntity.getIp() 相同, 另一 entity3.getSwitch() 与 newEntity.getVlan() 相同, 那么,
    changedFields 为null 而实际情况是对 entity3 的 vlan 进行的改变为 entity2 的 vlan , ip 改为 entity1 的 IP 了.

    待继续研究


###ClassState getClassState(IEntityClass clazz)

    查询是否在 classStateMap 中, 如果存在, 直接返回;如果不存在, 增加到  classStateMap. 返回增加的 classState

    
### void removeEntity(Entity removed,IEntityClass entityClass,Long deviceKey,Collection<Entity> others)

    从 this.secondaryIndexMap, this.classStateMap, this.primaryIndex 中不在 others 中, 符合 (removed , deviceKey) 条件的元素
    1. 删除 this.secondaryIndexMap.values() 中满足不在 others 中, 符合 (removed , deviceKey) 条件的元素
    2. 删除 this.classStateMap.get(entityClass.getName()).secondaryIndexMap.values() 中的元素, 也即 
perClassIndices 中元素组成的 DeviceMultiIndex(fields) 中满足不在 others 中, 符合 (removed , deviceKey) 条件的元素
    3. this.primaryIndex 中满足不在 others 中, 符合 (removed , deviceKey) 条件的元素
 
    注意: 此函数看似简单, 但关系极为复杂, 需要对 secondaryIndexMap, classStateMap, primaryIndex, ClassState, perClassIndices 的关系非常清楚. 更深层次是对 DeviceUniqueIndex 和 DeviceMultiIndex



###void processUpdates(Queue<DeviceUpdate> updates)
   
    遍历 updates 所有元素,  如果是 DELET 调用 removeDevice() 删除该设备, 否则, 新设备替代旧设备
    List<IDeviceListener> listeners = this.deviceListeners.getOrderedListeners();
    调研 notifyListeners(listeners, update); 通知每一个设备订阅者

####void notifyListeners(List<IDeviceListener> listeners, DeviceUpdate update)

    对每个实现订阅设备更新的 listener， 根据对设备的改变调用相应的方法。

##设备同步线程

    固定间隔时间(75 min), 检查每一个设备的 entity, 如果设备的所有 entity 都不在 primaryIndex 或 entityClassifier 就删除该设备

###Device learnDeviceByEntity(Entity entity)

    如果 entity 不存在 primaryIndex 和 secondaryIndexMap, 将 entity 加入 deviceMap, 并且将 entity 更新加入 deviceUpdates

    deleteQueue : 删除队列, 用于存储新设备更新失败

    查找 entity 对应的 deviceKey:
        如果 primaryIndex 中不存在,  entityClassifier 中不存在, 退出循环
        如果在 primaryIndex 中不存在, entityClassifier 中存在, classState.classIndex 中不存在
            如果 entity 的 switchPort 不为 null 且不是 topology 中的一个挂载点, 退出循环
            如果 entity 的 switchPort 是 null, 或 entity 不为 null 且是 topology 中的一个挂载点,
                利用 deviceKey 和 entity, entityClass 构造一个 New Device, 加入 deviceMap, 在 primaryIndex, secondaryIndexMap, ClassState 中更新
                如果 New Device 更新失败, 就加入 deleteQueue, 循环重新开始.
                如果 New Device 更新成功, 调用 updateUpdates() 之后退出循环

        如果在 primaryIndex 中不存在, entityClassifier 中存在, classState.classIndex 中存在
        或在 primaryIndex 中存在

            如果 deviceKey 不在 deviceMap 中, 循环重新开始
            如果 entity 的 switchPort 不为 null 且不是 topology 中的一个挂载点, 退出循环, 否则继续
            从 device 中获取 entity 的索引,
                如果 entity 存在, 设置 LastSeenTimestamp
                如果 entity 不存在, 构造 New Deivce 调用 deviceMap 中 new Device 代替旧 device updateSecondaryIndices(), updateUpdates()

            如果 entity 有 switchPort(拓扑存在对应的挂载点), 调用 device.updateAttachmentPoint() 检查是否更新, 如果更新, 调用 sendDeviceMovedNotification(device) , 否则, 什么也不作.

        最后 删除 deleteQueue 中的 Device, 调用 processUpdates(deviceUpdates) deviceSyncManager.storeDeviceThrottled(device) 处理更新

    待进一步全局理解

###boolean isEntityAllowed(Entity entity, IEntityClass entityClass)

    可以在这里增加自己的过滤机制

###boolean updateIndices(Device device, Long deviceKey)

    只有 primaryIndex 和 classState.classIndex 都更新成功才返回 true

###void updateSecondaryIndices(Entity entity,IEntityClass entityClass,Long deviceKey)

    更新　secondaryIndexMap.values() 和 getClassState(entityClass).secondaryIndexMap.values()

    问题: 与 updateIndices() 类似, 也应该返回 boolean. 或 log 错误


## PACKET_IN 消息

###Command receive(IOFSwitch sw, OFMessage msg,FloodlightContext cntx)

    接受 PACKET_IN 事件， 调用 processPacketInMessage()

###Command processPacketInMessage(IOFSwitch sw, OFPacketIn pi, FloodlightContext cntx)

    调用 srcEntity = getSourceEntityFromPacket(eth, sw.getId(), inPort) 从 PACKET_IN 中学习来源设备的信息, 如果来源设备 MAC 是广播或多播, 丢弃(停止对该包的处理)
    调用 learnDeviceFromArpResponseData(eth, sw.getId(), inPort) 从 PACKET_IN 中学习 arp 请求者的设备信息
    调用 srcDevice = learnDeviceByEntity(srcEntity), 从 ARP 请求中设备. 如果返回值为 null, 停止对该包的处理
    调用 dstEntity = getDestEntityFromPacket(eth) 根据目的 MAC 构造 Entity,
        如果返回值为 null, 继续.
        否则, findDestByEntity(srcDevice.getEntityClass(), dstEntity) 找到 dstDevice , 如果 dstDevice 不为null, 加入 fcStore
    调用 snoopDHCPClientName(eth, srcDevice)

    FloodlightContextStore<IDevice> fcStore = new FloodlightContextStore<IDevice>();

###IPv4Address getSrcIPv4AddrFromARP(Ethernet eth, MacAddress dlAddr)

    如果 eth 是 ARP 包, 且是

###IPv6Address getSrcIPv6Addr(Ethernet eth)

###Entity getSourceEntityFromPacket(Ethernet eth, DatapathId swdpid, OFPort port)

    学习转发 ARP 包的 entity:

    如果 eth 的源 MAC 是广播, 多播或 0, 返回 null.
    如果srcIP 或 srcIPv6 不为空, 返回 srcMac, srcIP(v4优先), vlan, swdpid, port 构造 Entity.
    如果 IP(v4,v6) 都为空, 返回 srcMac, vlan swdpid, port 构造的 Entity.

###Entity getDestEntityFromPacket(Ethernet eth)

    利用 eth 构造 Entity. 如果 eth 的目的 MAC 是广播, 多播或0, 返回null.

###LinkedList<DeviceUpdate> updateUpdates(LinkedList<DeviceUpdate> list, DeviceUpdate update)

    将 update 加入　list

###void learnDeviceFromArpResponseData(Ethernet eth,DatapathId swdpid,OFPort port)

    学习 ARP 包中的 entity

    如果 eth 的包体是 arp, 且 arp 是非多播或广播的 ARP 包, 且网卡源 MAC 与 ARP 报文的源 MAC 不同并且 arp
    发送者地址不为 0, 学习 arp 包发送者的设备信息并构造 Entity 变量, 调用 learnDeviceByEntity(entity)

    注意与 getSourceEntityFromPacket 的区别:
    learnDeviceFromArpResponseData 指学习发送 arp 请求的设备;
    而 getSourceEntityFromPacket 指学习转发 arp 请求的设备, 典型的是网关

###Device findDestByEntity(IEntityClass reference, Entity dstEntity)

    如果 primaryIndex 中找 dstEntity 到对应的 deviceKey, 返回  deviceMap.get(deviceKey)
    否则从 classStateMap.get(dstEntity.getName()).classIndex 中找 dstEntity 对应 deviceKey, 返回 deviceKey(当不为null)对应的 deviceMap.get(deviceKey)

    主: 目前官方只实现了 DefaultEntityClass. 如果没有自定义, 一般认为完全由 primaryIndex 决定

###void snoopDHCPClientName(Ethernet eth, Device srcDevice)

    只选择 eth 为 IPV4 UDP 的 DHCP 包, 且为 DHCP 请求包, DHCPOptionCode.OptionCode_Hostname 不为 null, 初始化
    srcDevice.dhcpClientName

-------------------------------------------------------------------

##SyncEntity implements Comparable<SyncEntity>

###变量 

    MacAddress macAddress
    IPv4Address ipv4Address
    VlanVid vlan
    DatapathId switchDPID
    OFPort switchPort
    Date lastSeenTimestamp
    Date activeSince


##DeviceSyncRepresentation

###变量

    private String key;
    private List<SyncEntity> entities

###DeviceSyncRepresentation(Device device)

    this.key = computeKey(device)
    this.entities : 如果 device.entities 中的元素e ， !e.hasSwitchPort() 
        或 isAttachmentPointEntity(aps, e) 或 e.getIpv4Address() != null 增加到 this.entities



###boolean isAttachmentPointEntity(SwitchPort[] aps, Entity e)

    aps 的端口是否在 e 中。


###computeKey(Device d)

    d.getEntityClass().getName()::d.getMACAddressString()::d.getVlanId()::d.getAttachmentPoints(true)::d.getIPv4Addresses()



##bug

这个构造函数需要捕获异常， 因为 System.arraycopy() 可能抛出异常

161     public Device(Device device, Entity newEntity, int insertionpoint) {
