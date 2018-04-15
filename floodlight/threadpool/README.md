# ThreadPool 分析

###设计的类

* IThreadPoolService.java
* ThreadPool.java 初始化线程
* OFMessageFuture.java 线程并发的调用相关
* OFSwitchBase.java queryStatistics() 使用线程

###IThreadPoolService.java

	import java.util.concurrent.ScheduledExecutorService;
	import net.floodlightcontroller.core.module.IFloodlightService;

	public interface IThreadPoolService extends IFloodlightService {
	    public ScheduledExecutorService getScheduledExecutor();
	}


###ThreadPool.java  //未增加异常处理，是否需要

后续的线程只需要实现 IThreadPoolService，并调用 getScheduledExecutor() 将获取
ScheduledExecutorService 的 executor

	import java.util.concurrent.ThreadFactory;
	import java.util.concurrent.Executors;
	import java.util.concurrent.ScheduledExecutorService;
	import java.util.concurrent.atomic.AtomicInteger;
	public class ThreadPool implements IThreadPoolService, IFloodlightModule {
		protected ScheduledExecutorService executor = null;

	    	// IThreadPoolService

		@Override
		public ScheduledExecutorService getScheduledExecutor() {
		    return executor;
		}

		@Override
		public void init(FloodlightModuleContext context)
		                             throws FloodlightModuleException {
		    final ThreadGroup tg = new ThreadGroup("Scheduled Task Threads");
		    ThreadFactory f = new ThreadFactory() {
		        AtomicInteger id = new AtomicInteger();
		        @Override
		        public Thread newThread(Runnable runnable) {
		            return new Thread(tg, runnable,
		                              "Scheduled-" + id.getAndIncrement());
		        }
		    };
		    executor = Executors.newScheduledThreadPool(5, f);
		}

		@Override
    		public void startUp(FloodlightModuleContext context) {
        	// no-op
    		}
	}

###SingtonTask.java 

    public class SingletonTask {
        protected static final Logger logger = 
                LoggerFactory.getLogger(SingletonTask.class);
                
        protected static class SingletonTaskContext  {
            protected boolean taskShouldRun = false;
            protected boolean taskRunning = false;

            protected SingletonTaskWorker waitingTask = null;
        }

        protected static class SingletonTaskWorker implements Runnable  {
            SingletonTask parent;
            boolean canceled = false;
            long nextschedule = 0;

            public SingletonTaskWorker(SingletonTask parent) {
                super();
                this.parent = parent;
            }

            @Override
            @LogMessageDoc(level="ERROR",
                           message="Exception while executing task",
                           recommendation=LogMessageDoc.GENERIC_ACTION)
            public void run() {
                synchronized (parent.context) {
                    if (canceled || !parent.context.taskShouldRun)
                        return;

                    parent.context.taskRunning = true;
                    parent.context.taskShouldRun = false;
                }

                try {
                    parent.task.run();
                } catch (Exception e) {
                    logger.error("Exception while executing task", e);
                }
                catch (Error e) {
                    logger.error("Error while executing task", e);
                    throw e;
                }

                synchronized (parent.context) {
                    parent.context.taskRunning = false;

                    if (parent.context.taskShouldRun) {
                        long now = System.nanoTime();
                        if ((nextschedule <= 0 || (nextschedule - now) <= 0)) {
                            parent.ses.execute(this);
                        } else {
                            parent.ses.schedule(this, 
                                                nextschedule-now, 
                                                TimeUnit.NANOSECONDS);
                        }
                    }
                }
            }
        }

        protected SingletonTaskContext context = new SingletonTaskContext();
        protected Runnable task;
        protected ScheduledExecutorService ses;


        /**
         * Construct a new SingletonTask for the given runnable.  The context
         * is used to manage the state of the task execution and can be shared
         * by more than one instance of the runnable.
         * @param context
         * @param Task
         */
        public SingletonTask(ScheduledExecutorService ses,
                Runnable task) {
            super();
            this.task = task;
            this.ses = ses;
        }

        /**
         * Schedule the task to run if there's not already a task scheduled
         * If there is such a task waiting that has not already started, it
         * cancel that task and reschedule it to run at the given time.  If the
         * task is already started, it will cause the task to be rescheduled once
         * it completes to run after delay from the time of reschedule.
         * 
         * @param delay the delay in scheduling
         * @param unit the timeunit of the delay
         */
        public void reschedule(long delay, TimeUnit unit) {
            boolean needQueue = true;
            SingletonTaskWorker stw = null;

            synchronized (context) {
                if (context.taskRunning || context.taskShouldRun) {
                    if (context.taskRunning) {
                        // schedule to restart at the right time
                        if (delay > 0) {
                            long now = System.nanoTime();
                            long then = 
                                now + TimeUnit.NANOSECONDS.convert(delay, unit);
                            context.waitingTask.nextschedule = then;
    //                        logger.debug("rescheduled task " + this + " for " + TimeUnit.SECONDS.convert(then, TimeUnit.NANOSECONDS) + "s. A bunch of these messages -may- indicate you have a blocked task.");
                        } else {
                            context.waitingTask.nextschedule = 0;
                        }
                        needQueue = false;
                    } else {
                        // cancel and requeue
                        context.waitingTask.canceled = true;
                        context.waitingTask = null;
                    }
                }

                context.taskShouldRun = true;

                if (needQueue) {
                    stw = context.waitingTask = new SingletonTaskWorker(this);                    
                }
            }

            if (needQueue) {
                if (delay <= 0) 
                    ses.execute(stw);
                else
                    ses.schedule(stw, delay, unit);
            }
        }
    }

###使用线程

由于 init 和 startUp 在模块加载的时候已经执行，所以，后续只要调用 getScheduledExecutor 方法，根据返回的 ScheduledExecutorService 对象，调用它的 schedule() 方法即可。
    
* 在模块开始定义  

    protected IThreadPoolService threadPoolService;
    protected SingletonTask discoveryTask;

* 在模块 inint 方法中初始化  
    
    threadPoolService = context.getServiceImpl(IThreadPoolService.class);

* 在模块 startUp 方法调用

    ScheduledExecutorService ses = threadPoolService.getScheduledExecutor();
    discoveryTask = new SingletonTask(ses, new Runnable() {
        @Override
        void run() {
             ....        
        }

    discoveryTask.reschedule(5,TimeUnit.SECONDS);