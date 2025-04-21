#include "solve_api.h"
#include <sstream>


std::string solver_api::handle_solve_request(std::string request){
    // get x
    int delimiter_pos = request.find('-');
    std::string x_str = request.substr(0, delimiter_pos + 1);
    request = request.substr(delimiter_pos + 1, request.size() - (delimiter_pos + 1));
    // get y
    delimiter_pos = request.find('-');
    std::string y_str = request.substr(0, delimiter_pos + 1);
    request = request.substr(delimiter_pos + 1, request.size() - (delimiter_pos + 1));
    // get z
    std::string z_str(request);

    int x = std::stoi(x_str);
    int y = std::stoi(y_str);
    int z = std::stoi(z_str);

    int res = this->solver.solve(x, y, z);
    if (res < 0){
        return("There was an error in finding the solution.\n");
    }else{
        std::stringstream ss;
        ss << "The solution is " << res << ".\n";
        return ss.str();
    }
}