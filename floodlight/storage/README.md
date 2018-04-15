这个模式是数据库操作的模块, 包括常用 SQL 操作 主要实现在文件 MemoryStorageSource.java NoSqlStorageSource.java
AbstractStorageSource.java 文件 

IStorageSourceListener 和 IStorageSourceService 实现了发布和订阅模式,
IStorageSourceService 通过 addListener 增加订阅者. 之后, 发布者发布 
rowsModified  rowsDeleted 消息, 当订阅者收到 rowsModified()  rowsDeleted() 
消息后可以决定如何操作.



#IStorageSourceListener.java

##IStorageSourceListener
* void rowsModified(String tableName, Set<Object> rowKeys)
* void rowsDeleted(String tableName, Set<Object> rowKeys)

#IStorageSourceService.java

##IStorageSourceService
* void setTablePrimaryKeyName(String tableName, String primaryKeyName)
* createTable(String tableName, Set<String> indexedColumns)
* Set<String> getAllTableNames()
* IQuery createQuery(String tableName, String[] columnNames, 
    IPredicate predicate, RowOrdering ordering)
* IResultSet executeQuery(IQuery query)
* IResultSet executeQuery(String tableName, String[] columnNames, 
    IPredicate predicate,RowOrdering ordering)
* Object[] executeQuery(String tableName, String[] columnNames, IPredicate predicate,
    RowOrdering ordering, IRowMapper rowMapper)
* void insertRow(String tableName, Map<String,Object> values)
* void updateRows(String tableName, List<Map<String,Object>> rows)
* void updateMatchingRows(String tableName, IPredicate predicate, Map<String,Object> values);
* void updateRow(String tableName, Object rowKey, Map<String,Object> values)
* void updateRow(String tableName, Map<String,Object> values)
* void deleteRow(String tableName, Object rowKey)
* void deleteRows(String tableName, Set<Object> rowKeys)
* void deleteMatchingRows(String tableName, IPredicate predicate)
* IResultSet getRow(String tableName, Object rowKey)
* void setExceptionHandler(IStorageExceptionHandler exceptionHandler);
* Future<IResultSet> executeQueryAsync(final IQuery query)
* Future<IResultSet> executeQueryAsync(final String tableName,
    final String[] columnNames,  final IPredicate predicate,
    final RowOrdering ordering)
* public Future<?> insertRowAsync(final String tableName, final Map<String,Object> values)
* Future<?> updateRowsAsync(final String tableName, final List<Map<String,Object>> rows)
* Future<?> updateMatchingRowsAsync(final String tableName, final IPredicate predicate,
    final Map<String,Object> values)
* Future<?> updateRowAsync(final String tableName, final Object rowKey,
    final Map<String,Object> values)
* Future<?> updateRowAsync(final String tableName, final Map<String,Object> values)
* Future<?> deleteRowAsync(final String tableName, final Object rowKey)
* Future<?> updateRowAsync(final String tableName, final Map<String,Object> values)
* Future<?> deleteRowAsync(final String tableName, final Object rowKey)
* Future<?> deleteRowsAsync(final String tableName, final Set<Object> rowKeys)
* Future<?> deleteMatchingRowsAsync(final String tableName, final IPredicate predicate)
* Future<?> getRowAsync(final String tableName, final Object rowKey)
* Future<?> saveAsync(final IResultSet resultSet)
* void addListener(String tableName, IStorageSourceListener listener)
* void removeListener(String tableName, IStorageSourceListener listener)
* void notifyListeners(List<StorageSourceNotification> notifications)

#AbstractStorageSource.java

##AbstractStorageSource

实现了 IStorageSourceService 接口, 该类的继承类只要实现里面的抽象方法即可

通过 executorService = Executors.newSingleThreadExecutor() 创建单例线程池, 
具体任务只要实现 class StorageCallable<V>  或 class StorageRunnable, 并加入 
executorService中, 实现异步调用.

目前不支持多线程操作数据库. 

###关键变量

Set<String> allTableNames : 所有表

static ExecutorService defaultExecutorService = Executors.newSingleThreadExecutor()
ExecutorService executorService = defaultExecutorService

其他模块

IStorageExceptionHandler exceptionHandler
IDebugCounterService debugCounterService
IRestApiService restApi

Map<String, IDebugCounter> debugCounters
Map<String, Set<IStorageSourceListener>> listeners


###void setExecutorService(ExecutorService executorService)
    
    设置线程池服务

###void setExceptionHandler(IStorageExceptionHandler exceptionHandler)

    设置异常处理器

###abstract void setTablePrimaryKeyName(String tableName, String primaryKeyName)

    设置表的主键

###void createTable(String tableName, Set<String> indexedColumns)

    allTableNames.add(tableName)

TODO: 增加数据库操作

###Set<String> getAllTableNames()
    
    获取所有表名

###void setDebugCounterService(IDebugCounterService dcs)
 
    设置 IDebugCounterService 服务

###void updateCounters(String tableOpType, String tableName)

    对 tableOpType 和 tableOpType__tableName 两技术器(如果不存在就增加)递增计数

###抽象方法

###abstract IQuery createQuery(String tableName, String[] columnNames, IPredicate predicate, RowOrdering ordering);
###abstract IResultSet executeQueryImpl(IQuery query)
###abstract void insertRowImpl(String tableName, Map<String, Object> values)
###abstract void updateRowsImpl(String tableName, List<Map<String,Object>> rows)
###abstract void updateRowImpl(String tableName, Object rowKey,Map<String, Object> values)
###abstract void updateRowImpl(String tableName, Map<String, Object> values)
###abstract void deleteRowsImpl(String tableName, Set<Object> rowKeys)
###abstract void deleteRowImpl(String tableName, Object rowKey)
###abstract IResultSet getRowImpl(String tableName, Object rowKey)


###IResultSet executeQuery(IQuery query)
   
    调用 return executeQueryImpl(query);

###IResultSet executeQuery(String tableName, String[] columnNames,
    IPredicate predicate, RowOrdering ordering)

    调用 createQuery(tableName, columnNames, predicate, ordering) 和 executeQuery(query);

###Object[] executeQuery(String tableName, String[] columnNames,
    IPredicate predicate, RowOrdering ordering, IRowMapper rowMapper)

    调用 executeQuery 之后转为数组

###Future<IResultSet> executeQueryAsync(final IQuery query)

    将任务 executeQuery(query) 加入线程池

###Future<IResultSet> executeQueryAsync(final String tableName,
    final String[] columnNames,  final IPredicate predicate,
    final RowOrdering ordering)

    将任务 executeQuery(tableName, columnNames,predicate, ordering) 加入线程池

###Future<Object[]> executeQueryAsync(final String tableName,
    final String[] columnNames,  final IPredicate predicate,
    final RowOrdering ordering, final IRowMapper rowMapper)

    executeQuery(tableName, columnNames, predicate, ordering, rowMapper) 加入线程池

###Future<?> insertRowAsync(final String tableName, final Map<String,Object> values)

    将任务 insertRow(tableName, values) 加入线程池

###void insertRow(String tableName, Map<String, Object> values)

    调用 insertRowImpl(tableName, values)

###Future<?> updateRowsAsync(final String tableName, final List<Map<String,Object>> rows)

    将任务 updateRows(tableName, rows) 加入线程池

###void updateRows(String tableName, List<Map<String,Object>> rows)

    调用 updateRowsImpl(tableName, rows)

###Future<?> updateMatchingRowsAsync(final String tableName, final IPredicate predicate, final Map<String,Object> values)

    将任务 updateMatchingRows(tableName, predicate, values) 加入线程池

###Future<?> updateRowAsync(final String tableName,final Object rowKey, final Map<String,Object> values)

    将任务 updateRow(tableName, rowKey, values) 加入线程池

###Future<?> updateRowAsync(final String tableName,final Map<String,Object> values)

    将任务 updateRow(tableName, values) 加入线程池

###Future<?> deleteRowAsync(final String tableName, final Object rowKey)

    将任务 deleteRow(tableName, rowKey) 加入线程池

###void deleteRow(String tableName, Object rowKey)

    调用 deleteRowImpl(tableName, rowKey) 

###deleteRowsAsync(final String tableName, final Set<Object> rowKeys)

    将任务 deleteRows(tableName, rowKeys) 加入线程池

###void deleteRows(String tableName, Set<Object> rowKeys)

    调用 deleteRowsImpl(tableName, rowKeys);

###Future<?> deleteMatchingRowsAsync(final String tableName, final IPredicate predicate)

    将任务 deleteMatchingRows(tableName, predicate) 加入线程池

###void deleteMatchingRows(String tableName, IPredicate predicate)

    调用 resultSet = executeQuery(tableName, null, predicate, null) 找到要删除的记录, 然后调用  resultSet.deleteRow() 删除之

###Future<?> getRowAsync(final String tableName, final Object rowKey)

    将任务 getRow(tableName, rowKey) 加入线程池

###IResultSet getRow(String tableName, Object rowKey)

    调用 getRowImpl(tableName, rowKey)
    
###Future<?> saveAsync(final IResultSet resultSet)

    将任务  resultSet.save() 加入线程池

###synchronized void addListener(String tableName, IStorageSourceListener listener)
    
    添加订阅者

###synchronized void removeListener(String tableName, IStorageSourceListener listener)

    删除订阅者

###synchronized void notifyListeners(StorageSourceNotification notification)

    发布者发布修改操作

###void notifyListeners(List<StorageSourceNotification> notifications)

    发布者发布修改操作
   
##NoSqlStorageSource 

    继承了 AbstractStorageSource 类

###关键变量

    Map<String,String>  tablePrimaryKeyMap : 存放(表名:主键)
    Map<String, Map<String,ColumnIndexMode>> tableIndexedColumnMap : 存放 (表名:(列:索引模式))

###void createTable(String tableName, Set<String> indexedColumns)

    调用父类的 createTable(tableName, indexedColumns)
    如果 indexedColumns 不为 null, 调用 setColumnIndexMode(tableName, columnName,ColumnIndexMode.EQUALITY_INDEXED) 设置索引模式

###void setTablePrimaryKeyName(String tableName, String primaryKeyName)

    tablePrimaryKeyMap.put(tableName, primaryKeyName)

###String getTablePrimaryKeyName(String tableName)

    tablePrimaryKeyMap.get(tableName), 如果不存在, 返回默认"id"

###ColumnIndexMode getColumnIndexMode(String tableName, String columnName)

    获取 tableName 列为 columnName 的索引模式

###void setColumnIndexMode(String tableName, String columnName, ColumnIndexMode indexMode)

    设置 tableName 列为 columnName 的索引模式为indexMode.

###getOperatorPredicateValue(OperatorPredicate predicate, Map<String,Comparable<?>> parameterMap)

    获取操作符的值, predicate.getValue() 或 parameterMap.get(predicate.getValue())

###convertPredicate(IPredicate predicate, String tableName, Map<String,Comparable<?>> parameterMap)

    递归遍历 predicate.getPredicateList(), 当元素是 OperatorPredicate 类型的时候, 调用 sincorporateComparison
合并操作. 未完待续

###NoSqlResultSet executeParameterizedQuery(String tableName, String[] columnNameList,IPredicate predicate, RowOrdering rowOrdering, Map<String,Comparable<?>> parameterMap)
    
    如果 noSqlPredicate != null 并且是有效的
        rowList = noSqlPredicate.execute(columnNameList)
    否则 getAllRows(tableName, columnNameList) 中满足条件的元素加入 rowList

    对 rowLists 根据 rowOrdering 排序

    调用 new NoSqlResultSet(this, tableName, rowList)

###IQuery createQuery(String tableName, String[] columnNameList, IPredicate predicate, RowOrdering rowOrdering)

    调用 new NoSqlQuery(tableName, columnNameList, predicate, rowOrdering)

###IResultSet executeQueryImpl(IQuery query)

    noSqlQuery = query
    调用 executeParameterizedQuery(noSqlQuery.getTableName(),noSqlQuery.getColumnNameList(), noSqlQuery.getPredicate(),noSqlQuery.getRowOrdering(), noSqlQuery.getParameterMap())


###void sendNotification(String tableName, StorageSourceNotification.Action action,List<Map<String,Object>> rows)

    rowskeys = row.get(primaryKeyName) for row in rows
    notifyListeners(new StorageSourceNotification(tableName, action, rowKeys))


###void sendNotification(String tableName,StorageSourceNotification.Action action, Set<Object> rowKeys)

    调用 notifyListeners(new StorageSourceNotification(tableName, action, rowKeys))

###void insertRowsAndNotify(String tableName, List<Map<String,Object>> insertRowList)
    
    调用 insertRows(tableName, insertRowList) 插入行
    调用 sendNotification(tableName, StorageSourceNotification.Action.MODIFY, insertRowList) 发送通知   

###void insertRowImpl(String tableName, Map<String, Object> values)

    调用 insertRowsAndNotify(tableName, rowList.addAll(values))

###void updateRowsAndNotify(String tableName, Set<Object> rowKeys, Map<String,Object> updateRowList)
    
    调用 updateRows(tableName, rowKeys, updateRowList) 更新行
    sendNotification(tableName, StorageSourceNotification.Action.MODIFY, rowKeys) 发布更新

###void updateMatchingRowsImpl(String tableName, IPredicate predicate, Map<String,Object> values)
    
    rowKey 为 executeQuery(tableName, {getTablePrimaryKeyName(tableName)}, predicate, null)
    调用 updateRowsAndNotify(tableName, rowKeys, values)     

###void updateRowImpl(String tableName, Object rowKey, Map<String,Object> values)    

    调用 updateRowsAndNotify(tableName, rowList.add(values).add(getTablePrimaryKeyName(tableName),rowKey))

###void updateRowImpl(String tableName, Map<String,Object> values)

    调用 updateRowsAndNotify(tableName, rowKeys.add(Values))

###void deleteRowsAndNotify(String tableName, Set<Object> rowKeyList)

    调用 deleteRows(tableName, rowKeyList) 删除行
    调用 sendNotification(tableName, StorageSourceNotification.Action.DELETE, rowKeyList) 发布更新

###void deleteRowImpl(String tableName, Object key)
    
    调用 deleteRowsAndNotify(tableName, keys)

###IResultSet getRowImpl(String tableName, Object rowKey)
    
    调用 getRow(tableName, null, rowKey)


###抽象方法

###abstract Collection<Map<String,Object>> getAllRows(String tableName, String[] columnNameList)
###abstract Map<String,Object> getRow(String tableName, String[] columnNameList, Object rowKey)
###abstract List<Map<String,Object>> executeEqualityQuery(String tableName,String[] columnNameList, String predicateColumnName, Comparable<?> value)
###abstract List<Map<String,Object>> executeRangeQuery(String tableName,String[] columnNameList, String predicateColumnName,Comparable<?> startValue, boolean startInclusive, Comparable<?> endValue, boolean endInclusive)
###abstract void insertRows(String tableName, List<Map<String,Object>> insertRowList)
###abstract void updateRows(String tableName, Set<Object> rowKeys, Map<String,Object> updateColumnMap)

##MemoryStorageSource 

存储模块, 继承了 NoSqlStorageSource, 该类实现了 NoSqlStorageSource 所有抽象方法

问题: 该类是不是应该是单例的?

###关键变量

    Map<String, MemoryTable> tableMap : (表名: MemoryTable)
    IPktInProcessingTimeService pktinProcessingTime : PACKET_IN 处理时间

###MemoryTable getTable(String tableName, boolean create)

    如果 tableName 不存在, 如果 create == true, 创建, 否则直接抛异常
    如果存在, 返回表

###Collection<Map<String,Object>> getAllRows(String tableName, String[] columnNameList)

    返回 tableMap.get(tableName, false).getAllRows()

###Map<String,Object> getRow(String tableName, String[] columnNameList, Object rowKey)

    返回 tableMap.get(tableName, false).getRow()

###List<Map<String,Object>> executeEqualityQuery(String tableName, String[] columnNameList, String predicateColumnName, Comparable<?> value)

    在 tableMap.get(tableName, false).getAllRows() 每一行row中查找 row.get(getpredicateColumnName) 与 value 相同的行

###List<Map<String,Object>> executeRangeQuery(String tableName,String[] columnNameList, String predicateColumnName,Comparable<?> startValue, boolean startInclusive, Comparable<?> endValue, boolean endInclusive)

    在 tableMap.get(tableName, false).getAllRows() 每一行row中查找 row.get(getpredicateColumnName) 在 startValue 和 endValue 之间的. startInclusive 和 endInclusive 用于是否包含相等的情况

###void insertRows(String tableName, List<Map<String,Object>> insertRowList)

    遍历 insertRowList 中的每一个元素 row :
    如果 row.get(getTablePrimaryKeyName(getTable(tableName, false))) 存在, 直接加入表中;
    否则, 创建新的记录, 加入数据库

###void updateRows(String tableName, Set<Object> rowKeys, Map<String,Object> updateRowList)

    将 updateRowList 中的所有元素加入 rowKeys 中的每一行中.
    getTable(tableName, false).getRow(rowKey).put([r.getKey(), r.getValue) for r in updateRowList])

###void updateRowsImpl(String tableName, List<Map<String,Object>> updateRowList)

    PrimaryKeyName = getTablePrimaryKeyName(tableName))
    遍历 updateRowList 中每一个元素 updaterow : 
    如果 row = getTable(tableName).getRow(updaterow.get(PrimaryKeyName)) 存在, row.put(update.getKey(), update.getValue())

    类似与上一方法

###void deleteRowsImpl(String tableName, Set<Object> rowKeys)

     从 getTable(tableName) 表中删除主键为 rowKeys 中的所有行

###void createTable(String tableName, Set<String> indexedColumnNames)

    调用父类的 super.createTable(tableName, indexedColumnNames)

###void setPktinProcessingTime(IPktInProcessingTimeService pktinProcessingTime)

    设置 this.pktinProcessingTime






##MemoryTable
PrimaryKeyName
    String tableName : 表名
    Map<Object,Map<String,Object>> rowMap : (记录:(主键:记录))
    int nextId : 下一条记录

* Integer getNextId()
* void deleteRow(Object rowKey)
* void insertRow(Object key, Map<String,Object> rowValues)
* Map<String,Object> newRow(Object key)
* Map<String,Object> getRow(Object key)
* Collection<Map<String,Object>> getAllRows()
* String getTableName()

    以上方法很简单,略

##NoSqlPredicate

    NoSqlStorageSource 的辅助抽象类

##NoSqlRangePredicate

    继承 NoSqlPredicate 

###关键变量

    NoSqlStorageSource storageSource
    String tableName
    String columnName
    Comparable<?> startValue
    boolean startInclusive
    Comparable<?> endValue
    boolean endInclusive

###boolean incorporateComparison(String columnName,OperatorPredicate.Operator operator, Comparable<?> value,CompoundPredicate.Operator parentOperator)

    没明白

###boolean isEqualityRange()

    没明白

###boolean canExecuteEfficiently()

    没明白

###List<Map<String,Object>> execute(String columnNameList[])

    如果 isEqualityRange() 为 True, 调用 storageSource.executeEqualityQuery(tableName, columnNameList, columnName, startValue)

    否则 storageSource.executeRangeQuery(tableName, columnNameList, columnName,startValue, startInclusive, endValue, endInclusive)

###Comparable<?> coerceValue(Comparable<?> value, Class targetClass)

    将 value 转为 targetClass 类类型

###boolean matchesValue(Comparable<?> value)

    将 value 转为 startValue 然后 与 startValue 比较
    将 value 转为 endValue 然后 与 endValue 比较

###boolean matchesRow(Map<String,Object> row)

    调用 matchesValue(row.get(columnName))

##NoSqlOperatorPredicate

    继承 NoSqlPredicate 

##关键变量

    NoSqlStorageSource storageSource    : 存储资源
    String columnName                   : 列名
    OperatorPredicate.Operator operator : 操作符
    Object value                        : 值

###boolean incorporateComparison(String columnName, OperatorPredicate.Operator operator, Comparable<?> value, CompoundPredicate.Operator parentOperator)

    未实现

###boolean canExecuteEfficiently()
    
    未实现

###List<Map<String,Object>> execute(String columnNames[])

    未实现

###boolean matchesRow(Map<String,Object> row)

    未实现

##NoSqlCompoundPredicate

    继承 NoSqlPredicate 

###关键变量

    NoSqlStorageSource storageSource    :
    CompoundPredicate.Operator operator :
    boolean negated                     :
    String tableName                    :
    List<NoSqlPredicate> predicateList  :

###canExecuteEfficiently()

    如果 operator == CompoundPredicate.Operator.AND, 只要 predicateList 有一个是  canExecuteEfficiently() 返回 true

    否则 只要 predicateList 有一个不是 canExecuteEfficiently() , 返回 false

###List<Map<String,Object>> combineRowLists(String primaryKeyName, List<Map<String,Object>> list1, List<Map<String,Object>> list2, CompoundPredicate.Operator operator)

    list1 和 list2 根据主键进行排序后, 遍历 list1 和 list2 : 
    如果 operator == CompoundPredicate.Operator.AND, 返回相同记录的列表
    否则 返回两条记录的较小者或者非 null 的列表

###List<Map<String,Object>> execute(String columnNames[])

    遍历 predicateList : 
    如果 canExecuteEfficiently() , 调用 combineRowLists() 获取之前所有元素的execute()与当前元素execute() 的 combinedRowList 
    否则 加入名为 inefficientPredicates 的HashSet

    遍历 combinedRowList, 如果由元素在 inefficientPredicates 中加入 filteredRowList 中

###boolean matchesRow(Map<String,Object> row)

    如果 operator == CompoundPredicate.Operator.AND 则 predicateList 里面的每个元素 predicate.matchesRow(row) 都为 true, 才返回 true

    否则, predicateList 有一个元素 predicate.matchesRow(row) 为 true, 就返回 true

    

##RowComparator

    NoSqlCompoundPredicate 的辅助类, 实现 Comparator 接口

###关键变量

    primaryKeyName : 主键名

###int compare(Map<String,Object> row1, Map<String,Object> row2)

    比较 row1.get(primaryKeyName) 与 row2.get(primaryKeyName)








##谓词
 
##IPredicate

    数据库谓词接口类

    public interface IPredicate {
    }

##OperatorPredicate

    预算符谓词，实现 IPredicate 接口

###关键变量

    String columnName　: 列名
    Operator operator　: 运算法
    Comparable<?> value : 值

###String getColumnName()

    获取列名

###Operator getOperator()

    获取运算符

###Comparable<?> getValue()

    获取值


##CompoundPredicate

    组合谓词，实现 IPredicate 接口

###关键变量
   
    Operator operator  // AND OR
    boolean negated    // NOT
    IPredicate[] predicateList //谓词列表

###Operator getOperator()

    获取 operator

###boolean isNegated()

    获取 negated

###IPredicate[] getPredicateList()

    获取 predicateList

##行排序

##RowOrdering

###关键列表

    List<Item> itemList //item 列表, 一行由 itenList 组成

###void add(String column)
###void add(String column, Direction direction)
###void add(Item item)
###void add(Item[] itemArray)
###void add(List<Item> itemList)

    以上类都是增加一个 item 到 itemList

###List<Item> getItemList()

     获取所有的 item

##Item

    RowOrdering的辅助类

###关键列表

    String column //列名
    Direction direction //排序方式,包含 ASCENDING, DESCENDING

###String getColumn()
###Direction getDirection()
###RowOrdering getOuterType()

    以上方法见面知意

##查询

##IQuery

    查询接口类

    public interface IQuery {

        String getTableName()
        void setParameter(String name, Object value)
    }

##NoSqlQuery

###关键变量

    String tableName  : 表名
    String[] columnNameList : 列名的列表
    IPredicate predicate    : 谓词
    RowOrdering rowOrdering : 行排序
    Map<String,Comparable<?>> parameterMap : 参数

###void setParameter(String name, Object value)

    增加 map,value 到 parameterMap 

###String getTableName
###String[] getColumnNameList()
###IPredicate getPredicate()
###RowOrdering getRowOrdering()
###Comparable<?> getParameter(String name)
###Map<String,Comparable<?>> getParameterMap()

    以上方法见面知意

##结果集

##IResultSet

    结果集合类, 继承了迭代器　Iterator<IResultSet>

* void close()
* boolean next()
* void save()
* Map<String,Object> getRow()
* void deleteRow()

##IRowMapper

    结果集对应的类对象

* Object mapRow(IResultSet resultSet)

##ResultSetIterator

    结果集，实现了迭代器　Iterator<IResultSet>

###关键变量

    IResultSet resultSet //结果集
    boolean hasAnother   //下一个是否有元素
    boolean peekedAtNext //是否切换到下一个元素

###IResultSet next()

    到达下一个元素

###boolean hasNext()
    
    下一个是否存在

###void remove()

    不支持

###NoSqlResultSet

    实现了 IResultSet

###关键变量
   
    NoSqlStorageSource storageSource
    String tableName                      :表名
    String primaryKeyName                 :主键
    List<Map<String,Object>> rowList      :所有行
    int currentIndex
    Map<String,Object> currentRowUpdate   :(主键:记录)
    List<Map<String,Object>> rowUpdateList:保存 currentRowUpdate
    Set<Object> rowDeleteSet              :保持待删除的记录
    Iterator<IResultSet> resultSetIterator:结果的迭代器

###void addRow(Map<String,Object> row)

    增加到 rowList

###Map<String,Object> getRow()

    rowList.get(currentIndex)

###boolean containsColumn(String columnName)

    调用 getObject(columnName), rowList.get(currentIndex).get(columnName)

###void endCurrentRowUpdate()

    将 currentRowUpdate 增加到 rowUpdateList    
    
###void close()

    什么也不做

    问题: 未实现?

###boolean next()

    将 currentRowUpdate 增加到 rowUpdateList, 递增 currentIndex

###void save()
    
    将 currentRowUpdate 增加到 rowUpdateList
    将 rowUpdateList 更新作用于数据库
    将 rowDeleteSet 更新作用于数据库

###void addRowUpdate(String column, Object value)

        如果 currentRowUpdate 为 null, 初始化 currentRowUpdate
    (column:value) 增加到 currentRowUpdate 中

###void deleteRow()

    将当前记录加入rowDeleteSet中. 即将 rowList.get(currentIndex).get(primaryKeyName) 增加到 rowDeleteSet 中

###Iterator<IResultSet> iterator()

    返回 ResultSetIterator 的迭代器

##发布者

##StorageSourceNotification

    存储资源通知类

###关键变量

    String tableName : 表名
    Action action :  对表的操作: MODIFY, DELETE
    Set<Object> keys : 表中的记录

* String getTableName()
* Action getAction()
* Set<Object> getKeys()
* void setTableName(String tableName)
* void setAction(Action action)
* void setKeys(Set<Object> keys)

##SynchronousExecutorService

    实现　ExecutorService　接口

###void shutdown()
###List<Runnable> shutdownNow()
###boolean isShutdown()
###boolean isTerminated()
###boolean awaitTermination(long timeout, TimeUnit unit)

    以上方法，没有实现，不要调用

###<T> List<Future<T>> invokeAll(Collection<? extends Callable<T>> tasks)

    将　tasks 加入线程池，返回获取结果的对象列表．

###<T> List<Future<T>> invokeAll(Collection<? extends Callable<T>> tasks, long timeout, TimeUnit units)

    直接调用　invokeAll(task)
    问题：没有完全实现

###<T> T invokeAny(Collection<? extends Callable<T>> tasks)

    遍历　tasks, 调用　task.call() 

    问题: 没有完全实现

###<T> T invokeAny(Collection<? extends Callable<T>> tasks, long timeout, TimeUnit units)

    调用 invokeAny(tasks)

###<T> Future<T> submit(Callable<T> callable)

    callable.call() 
    如果没有错误, result 初始化 SynchronousFuture
    否则用 异常初始化 SynchronousFuture

###Future<?> submit(Runnable runnable)

    runnable.run()
    如果没有错误, result 初始化 SynchronousFuture
    否则用 异常初始化 SynchronousFuture

###<T> Future<T> submit(Runnable runnable, T result)

    runnable.run()
    如果没有错误, result 初始化 SynchronousFuture
    否则用 异常初始化 SynchronousFuture

###void execute(Runnable command)

    command.run()

##SynchronousFuture

    实现　Future　接口，　SynchronousExecutorService　的辅助类

###关键变量

    T result  // 结果
    Exception exc　//异常

###boolean cancel(boolean mayInterruptIfRunning)
    
    返回 false

    问题: 是故意屏蔽，还是，未实现，但确定

###boolean isCancelled()

    返回 false

    问题: 是故意屏蔽，还是，未实现，但确定


###boolean isDone()
    返回　true

    问题: 是故意屏蔽，还是，未实现，但确定

###T get()

    如果　exec 不为　null, 返回　result

###T get(long timeout, TimeUnit unit)

    调用　get()