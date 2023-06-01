// Example Pixel Shader

uniform float uWindDir;

//this is a parameter you can put in to easily rotate the compass to your given axes
//we just subtract this number from the input 
uniform float uNorthOffset; 

#define PI 3.141592653589

out vec4 fragColor;
void main()
{
	float rad = (uWindDir - uNorthOffset) * PI / 180.0;
	vec2 dir = -vec2(cos(rad), sin(rad));
	vec4 color = vec4(dir, 0, 1.0);
	fragColor = TDOutputSwizzle(color);
}
