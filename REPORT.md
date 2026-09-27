


## Complete run

https://github.com/saakolch/ML_Pro_2026_assignment_1/pkgs/container/ml_pro_2026_assignment_1

![green run](images/green_run.png)

## Branch with red and green tests

pull: https://github.com/saakolch/ML_Pro_2026_assignment_1/pull/1

## 2.3  Changing model path in configMap

### Поменял ссылку, но ничего не сломалось, не очень понимаю почему, но думаю, что ссылка тащится из конфига 
![alt text](images/configMap_error.png)

## 2.3 Broken secret 

red: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326046542/job/108639065980
-> deploy is red, можно видеть через kubectl logs <pod-name>

green: https://github.com/saakolch/ML_Pro_2026_assignment_1/actions/runs/36326320274

