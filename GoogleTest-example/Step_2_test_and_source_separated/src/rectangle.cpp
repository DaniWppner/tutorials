#include "rectangle.h"

rectangle::rectangle(int _base, int _height)
{
    this->base = _base;
    this->height = _height;
}

int rectangle::get_perimeter(){
    return this->base*2 + this->height*2;
}

rectangle::~rectangle()
{
}
