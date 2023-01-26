# Problem statement
The sessionization in data-systems is the act of turning event-based data into sessions.
A session then is an ordered list of actions performed by the session entity (i.e. user).
Ultimately, a session is either terminated by inactivity or by the session entity completing the task.

Sessions are part of the behavioral analytics patterns exposing the users behavior to the product.
Capturing user actions in real time allows to react to these almost immediately.

In this project producers produce raw data which is consumed and cleaned. 
After the cleaned data is again exposed to a new topic it is consumed by an application that turns these events into sessions.
In this case a user session will be defined as all pages visited by a single user.
This will allow to compute a number of aggregates such as popular pages, visited pages per visit across all users.

# Stateful processing
Sessionization is part of a wider group of streaming processing problems called stateful processing.
A stateful process is performed in the context of previous transactions.
Thus, the result of a stateful process depends on previous events that belong to the same state.
In contrast, a stateless process performers identically, independent of previous events.
Therefore, the logic of a stateful process is a lot more complicated and a number of key points have to be considered:
- **Ingestion logic**: Under which rule should incoming data be associated to a specific state?
- **Stateful logic**: What action should be performed based in the incoming data and previous events?
- **State store**: How and where should the state be saved to ensure performance and fault-tolerance
- **State expiration**: What is the terminating condition of a state, such as a specific action or inactivity?

There are two main stateful processing types:
- **Window-based processing**: A window defines a time interval in which incoming data is associated to the same state depending on its value of the timestamp field.
There are however different types of windows such as a tumbling window (discrete non-overlapping time intervals of equal length), 
hopping window (discrete overlapping time intervals of equal length) or sliding window (continuous and therefore overlapping time intervals of equal length).
Thus, depending on the window configuration an incoming event can be associated to different or multiple windows.
- **Arbitrary stateful processing**: Describes the general approach to a stateful process.
  - Define the property that is used in the collection layer
  - Group the input events with the *group by key* expression
  - Determine what should happen to the accumulated data in the data transformation component
  - There are two major transformation functions: One is concerned with updating the state and storing it in the data store while the other one takes the state data and transforms it to the final output.
  - Perform the transformation on top of the input data by looking up the previous state in the state store, performing the transformation logic and then updating the state
  - Apply the explicit or implicit state expiration rule.
Per state, the expiration condition can also be saved to the state in order to determine whether to generate output

As for now, arbitrary stateful processing is not possible in the Apache Spark framework using python.
However, this will change with release of [Spark 3.4](https://www.databricks.com/blog/2022/10/18/python-arbitrary-stateful-processing-structured-streaming.html?utm_source=bambu&utm_medium=social&utm_campaign=advocacy&blaid=3706982) in February 2023.

It would be very expensive to build the state store as a distributed data store,
since querying it would create a lot of costly network traffic.
There are however less resource intensive implementations:
- **Using the main memory of the stateful application**:
Storing the state on a volatile memory is dangerous.
If the compute node fails, the state will be lost.
Therefore, the state store is often backed up in a distributed file system or object store.
Apache spark structured streaming uses an in-memory map to store the last entries of the keys and a hdfs compatible file system to store all state changes made in every micro batch.
Thus, Apache spark will keep an in-memory hashmap of the most recent values of the every state group and will load it from memory in the lookup stage.
Afterwards the hashmap will be updated.
To ensure fault tolerance, only the modified states are saved in a hdfs-compatible file system.
For every partition and per task one file will be created.
In case the application crashes, the hashmap will be recomputed by loading all checkpoint files beginning from the oldest.
This approach is also called **in-memory on-heap with a fault tolerance backup**.
- **Using an embedded database**:
The database is hosted on the same compute node as the application but is not managed by the same framework.
Thus, while some part of the memory of the worker is dedicated to the application, another part is also dedicated to the database.
Hence, when the framework fails, the state can be loaded from the database.
This approach is also called **in-memory off-heap with a fault tolerance backup**.

The main difference between **on-heap** and **of-heap** is that if the state store is stored in the data processing framework extra pressure will be added to the process managing the memory (called garbage collector).
It will not only have to deal with the temporary task data but also with the expired states.
This will lead to longer garbage collection pauses and therefore slow down the data processing or at least make them less predictable.
If the data computation and state storage are separated a more predictable data processing will be achieved.
Here as well the whole node can fail and the state will be lost.
Thus, the embedded state store is backed up to a more resilient and fault-tolerant storage.
This comes into effect especially in very large data sets.
The best approach is to start simple and continue from there to not over-complicate things.
The off-heap solution adds another component to the system, increasing the required maintenance effort and increasing the overall complexity.

- **Using a remote fast-access database:** A typical candidate would be a key-value store providing fast access.
The workers or applications then retrieve the states from the database.
One scenario is when there is no data processing framework but some kind of serverless functions in docker containers.
These are distributed on the cloud and can be considered to fail at any moment so the work has to be taken over by another node.
In this case using a key-value data store is a valid solution.
One major drawback is that this solution requires a lot of custom code and adds a lot of complexity to the overall architecture.

Regarding computing the state there are two general approaches:
- **incremental**: The already accumulated state is combined with the new input data.
Thus, with every computation step we get the new final state information.
To use this approach, the state stored in the state store is only small for a low memory pressure on the application.
In addition, there is only one data structure that has to be managed and there is no intermediary state (such as with the cumulative approach).
Since it is not oder-sensitive so late data is not an issue.
However, this approach is not always possible to use.
- **cumulative**: In the case that the incoming data is not simply additive, the cumulative approach has to be used.
Thus, these cases are order-sensitive and the problem of late data has to be mitigated.
This however means, that an intermediary state has to be stored.
Finally, to generate the output, all intermediate states associated to the same session have to be accumulated.
Since this approach increases to memory pressure on the application it is necessary to minimize the pressure as much as possible.
One point is to only store the required information in the intermediary state store.

# Shuffle
Shuffling describes the action to move data between worker nodes in order to make some computation.
This depends on the transformations performed on the data.
If only filtering and mapping transformations are performed on the data then the data will remain on the same physical node.
However, when expressions such as *groupByKey*, *join*, *repartitionDataset* are used, some shuffling will be done.

For example when we want to compute a user activity for the last two weeks we wil need to move the data associated to the user to the same computation node.

While shuffling is in some cases inevitable, it should be avoided as much as possible.
Since the data has to be moved across the network it will always slow down the processing in some way.
One way to avoid shuffling is to partition the data correctly before grouping it.
Since the data that needs to be grouped is in the same partition it does not have to be accumulated from other computation nodes throughout the network.
Thus, the optimal way incoming data should be partitioned is highly dependent on the following data transformations.

# Late Data
Data is considered to be late if the difference between action and real time is too big for integration the action into the pipeline.
In other words, the event time is much smaller than the processing time.
Thus, whether the data is too late or not depends on the processing capabilities of the data consumers.

To handle late data Apache spark structured streaming uses watermarks.
The watermark defines how late a given event can be.
First a threshold value has to be defined which describes how late can be.
Then, for every incoming micro batch all events will be discarded that have an event time less than the watermark (if it already exists).
Afterwards the maximum event time is taken from all remaining events and the new watermark is calculated by subtracting the threshold value from the newest event time.

# Scalability
Predicting the load of a data pipeline is quite hard and can change over time.
If the load maximum is reached the system has to be scaled in order to keep working properly.
A system can either be scaled vertically or horizontally.
Vertical scaling occurs on the hardware level and basically means increasing the computing capabilities of the server.
Horizontal scaling on the other hand means to increase the number of computation nodes instead of replacing existing nodes with more powerful versions.

In order to decide whether to scale horizontally or vertically we introduce scaling policy:
- The simplest realisation would be to define static rules that add or remove computing power from the data processing logic.
This is an accurate approach when the load is predictable.
- Another approach uses the metrics of hardware resources.
In this case we define one or multiple resources to observe and define a threshold that will trigger the scaling action.
- The final strategy is to write custom code and define scaling metrics.
Although this approach requires the most work it also allows the definition of the best metrics.

In addition to defining a scaling policy it is necessary to define a cool down period.
This period defines the minimum time interval in which either an up-scaling or down-scaling method can be performed.
This helps to avoid consecutive scaling actions in a very short time period in the case of large load variation.

Finally, a latency is necessary, that will hold back the scaling for some time in order to avoid scaling only for a very short load peak.
This will help to avoid unnecessary scaling.

**Elasticity** is a special subcategory of horizontal scalability and is also known as auto-scaling.
While the previous approaches were mainly concerned with increasing more hardware resources, 
elasticity is the ability of a data processing framework to create more compute processes in order to handle extra load,
ideally without any human intervention

In the following two elasticity methods are presented:
- Framework Dataflow by GCP: 
The data processing job (batch or streaming) will adapt the number of worker nodes according to the load.
In addition, the maximum number of workers can be defined to limit the resources used.
- Framework Apache Spark:
Elasticity is provided by **Dynamic Resource Allocation**.
The idea is similar the Dataflow.
Apache Spark divides the computation process into multiple tasks.
Depending on the number of workers, each task will be assigned to one of them.
In regular intervals, the framework checks the backlog for idle workers.
If any exist for too long, new workers will be created to handle the load.
Also, idle workers will be destroyed if no task can be assigned to them.
Thus, the latency of task computation can be controlled by how long the framework should wait until new workers should be added.

Since elasticity only works when physical computation resources are available, this approach needs to be combined with an automatic scaling policy.

# Data Reprocessing
It is inevitable that things will go wrong one day.
The main reasons for reprocessing are:
- Missing input data:
This usually happens when the point of data entry is not managed by the same team as the data pipeline.
- Issues in the processing logic:
This occurs when for example a new version of the code is submitted, containing a small bug.
After publishing the bugfix the incoming data during the period where the buggy version was deployed needs to be reprocessed.
- An exception:
For instance of a hardware of server issue or receiving an incorrectly formatted field and not being prepared for this in the code.

Reprocessing static data is most times not very complicated, especially if the data is partitioned.
It is sufficient to relaunch the process with an older execution time.
It is however more challenging for streaming pipelines:
- Stop the pipeline and fix the issue:
There is no need to reprocess the data if the business logic doesn't change for the past, only the latency is increased.
- Reprocess the past data:
This is a bit more complicated and requires an idempotent output storage (aliases or partitioned data stores).
- Running streaming pipeline as a batch:
Most data processing frameworks have the same API abstraction for streaming and batch processing.
Thus, by changing the data source the dataset can be processed as a batch.
This approach however requires some custom coding.

# Complex Event Processing

For streaming processing we need at least one source and one consumer.
In the case of a single source and single consumer, it is also referred to as event stream.
In Complex Event Processing (CEP) there are at least two sources.
Such an architecture is also called an event cloud.

With multiple sources, events can not only be processed unitary but can also be correlated to events coming from other sources in order to find some behavioral patterns.
Instead of a second source a static data store with a reference dataset can be combined with the CEP computation layer.

The core of the CEP computation layer is called the rules engine.
These rules will be applied to each incoming event by the processing framework.
For each rule, an event can create multiple outbound actions.
Thus, the rules apply some meaning to the incoming data.

The key-element of any CEP framework is the pattern.
The CEP architecture looks similar to a simple event-driven architecture. 
There are however some characteristics that help to distinguish between a simple and a complex event processing architecture.
- CEP handles multiple data sources that often expose different layers of abstraction.
By combining these, a meaningful outbound action can be determined. 
- The CEP is business driven.
The rules are defined by business stakeholders with the goal to optimize business use-cases.
Thus, the rules engine is often managed by business users.
Sometimes there is also a graphical interface in which they can configure new rules that then will be translated into programming logic. 
- A CEP system works with low latency data.
Therefore, the main data source should be based on a streaming engine.
Static data is only used as a reference data store.

# Messaging Patterns
There are a number of common patterns one will encounter when working with streaming technologies:
- **Dead Letter Queue**:
Used for messages that cannot be processed either because of incomplete data, wrong format or due to generating some unexpected exception.
These events are classified as *invalid* and taken out of the stream to be handled individually.
This can not only be seen in streaming applications but also with batch processing.
In this case, the invalid data is then saved in a *Dead Letter Table* or similar.
- **Content Enricher**:
Used to add an extra valuable information to the data and avoid fetching this data every time by the downstream consumers.
- **Envelope Wrapper**:
Used to add extra data and metadata, without overwriting the original event.
- **Invalid Message Channel**:
A more business rule-oriented version of the Dead Letter Queue.
The invalid data is often redirected to another place after performing some business rule validation.
An example might be an invalid email address or other values that are invalid from a business point of view.
- **Message Dispatcher**:
Heterogeneous events initially stored in a single place are routed to more dedicated stores.
For example the events *order*, *payment*, *cancellation* are separated and sent to different topics.
- **Message expiration**:
Invalidate messages regarding some time-based condition.
For example the consumer checks the event time to filter out too old messages and send them to a separate queue.
This can be mixed with *Invalid Message Channel* for the storage of too old records.

# Tips For Debugging Data Processing Code
These tips can be applied globally to all jobs related to data processing.
- Start by exploring the data set.
Even if the schema is known, the data should be explored to find patterns, different exceptions to business rules, etc.
- Data is not perfect and sooner or later the data inconsistencies will come up.
After exploring the data develop the logic iteratively.
Doing small steps helps to discover and debug problems quicker.
- Test often and soon.
Especially the feedback at the beginning to the development wil drive the design decisions.
Thus, this helps to adapt soon and prevent from breaking and restarting from scratch.
- Follow software engineering principles such as unit test, responsibility separation and simplicity.
- Monitor and log everything that can help to reproduce the problem locally and understand it.
This can not only be useful in production but also during development.
Logs can help to understand bugs, and it is always good to first understand be error without relaunching the pipeline.