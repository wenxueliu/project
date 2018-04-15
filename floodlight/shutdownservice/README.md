每个调用 registerShutdownListener() 注册服务的模块, 都需要实现 floodlightIsShuttingDown(), 这样在
ShutdownServiceImpl调用 terminate() 的时候, 会调用对应模块的 floodlightIsShuttingDown() 方法.

#ShutdownServiceImpl.java

##ShutdownServiceImpl

###变量说明

    final CopyOnWriteArrayList<IShutdownListener> shutdownListeners

###void registerShutdownListener(@Nonnull IShutdownListener listener)

    将 listener 加入 shutdownListeners

###void terminate(@Nullable final String reason, final int exitCode)

    所有情况下调用, exitCode = 0 表示正常, 其他表示异常

    1. 创建一个 Thread, log.error 信息, 此现场不会被中断.
    2. 遍历 shutdownListeners 中的每个监听器 listener, 调用 listener.floodlightIsShuttingDown();
    3. 最后调用 System.exit(exitCode)

###void terminate(final String reason, final Throwable e, final int exitCode)

    异常情况下调用

    1. 创建一个 Thread, log.error 信息, 此现场不会被中断.
    2. 遍历 shutdownListeners 中的每个监听器listener, 调用 listener.floodlightIsShuttingDown();
    3. 最后调用 System.exit(exitCode)