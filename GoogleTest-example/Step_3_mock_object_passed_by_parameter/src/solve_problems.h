
class complex_problem_solver
{
public:
    complex_problem_solver(){};
    virtual ~complex_problem_solver(){};
    virtual int solve (int x, int y, int z) = 0;
};
