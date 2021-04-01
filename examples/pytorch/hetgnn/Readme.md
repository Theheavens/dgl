# DGL Implementation of the HetGNN

This is a demo implemention of the HetGNN model proposed in the paper [Heterogeneous Graph Neural Network](https://dl.acm.org/doi/10.1145/3292500.3330961). 

It will be integrated into an open toolkit, so it will not be merged into the dgl-master. And it just gives an example to someone who is interested in the dgl implementation of the paper.

## Dependencies

- pytorch 1.7.1
- dgl 0.6

## Datasets

- We use the academic dataset released by the [author](https://github.com/chuxuzhang/KDD2019_HetGNN/tree/master/data/academic).
  - For author link prediction
    - a_a_list_test.txt
    - a_a_list_train.txt
- We process the dataset and save it as dgl.heterograph
  - Get academic.bin by using below command
  - wget https://s3.cn-north-1.amazonaws.com.cn/dgl-data/dataset/academic.bin

## Demo Usage

```
python run.py
```

Hyperparameter can be modified in the file *config.ini*.

## Notice

##### Sampling Heterogeneous Neighbors(C1)

​			Hetgnn_graph() will build the graph used in the aggregate neighbors and will be saved as dgl.graph

##### HetGNN-model contains two components:

- Encoding Hetergeneous Contens(C2)
- Aggregating Heterogeneous Neighbors(C3)
  - Same Type Neighbors Aggregation
  - Types Combination



## Results

| A-II(type-1) authors link prediction | AUC    | F1     |
| ------------------------------------ | ------ | ------ |
| paper                                | 0.717  | 0.669  |
| dgl                                  | 0.7175 | 0.7178 |

| Node classification | Macro-F1 | Micro-F1 |
| ------------------- | -------- | -------- |
| paper               | 0.978    | 0.979    |
| dgl                 | 0.9701   | 0.9705   |