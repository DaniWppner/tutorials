#include "solve_problems.h"
#include <string>

class solver_api{
private:
    complex_problem_solver& solver;
public:
    solver_api(complex_problem_solver& _solver) : solver(_solver){};
    std::string handle_solve_request(std::string request);
};