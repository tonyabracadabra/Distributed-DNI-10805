service LinearModel {
    void initialize(1:string conf)
    void update(1:string trueGrad, 2:string id),
    string predict(1:string h, 2:string id),
}