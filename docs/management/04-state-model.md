# 状态模型


## 状态定义


|状态|说明|
|-|-|
|candidate|候选|
|reviewed|已审查|
|frozen|冻结|
|effective|生效|
|deprecated|废止|


---

## 状态转换
candidate
    |
    v
reviewed
    |
    v
frozen
    |
    v
effective
    |
    v
deprecated


---

## 禁止转换

禁止：

candidate -> effective

除非明确包含冻结确认。


