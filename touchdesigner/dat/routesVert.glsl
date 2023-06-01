uniform float uAlphaFront;
uniform float uShadowStrength;
uniform vec3 uShadowColor;
uniform vec3 uDiffuseColor;
uniform vec3 uAmbientColor;
uniform vec3 uSpecularColor;
uniform float uShininess;
uniform vec3 uRouteColor;


uniform float uTime;
uniform vec3 uTurb; //weight, time scale, xy scale

uniform sampler2D sTurb;

uniform samplerBuffer uPoints;

uniform sampler2D sPos;
uniform sampler2D sUnrolledRoutes;

// uniform vec2[437344] uPoints;

out Vertex
{
	vec4 color;
	vec2 uv;
	vec3 worldSpacePos;
	vec3 worldSpaceNorm;
	float adsr;
	float weight;
	flat int cameraIndex;
} oVert;

ivec2 index_to_uv(int idx, vec2 res){
	int x = int(floor(fract(idx / res.x) * res.x));
	int y = int(floor(idx / res.y));

	return ivec2(x,y);
}

void main()
{


	int id = TDInstanceID();
	int vtx = gl_VertexID;

	gl_PointSize = 1.0;
	// First deform the vertex and normal
	// TDDeform always returns values in world space
	vec3 newP = P;
	vec3 uvUnwrapCoord = TDInstanceTexCoord(TDUVUnwrapCoord());
	//grab num pionts for route from route lookup 
	vec4 routeData = vec4(TDInstanceCustomAttrib0()); // pts in route, start lookup index offset, adsr

	oVert.color.rgb = uRouteColor.rgb;
	oVert.color.a = 1;
	// // This is here to ensure we only execute lighting etc. code
	float alpha = 1.;

	// we want to just skip instances not filled with event data, with a pts value of -1
	if(routeData.x <0){
		newP.xy = vec2(0);
		alpha = 0.0;
	}else
	{
		if(vtx < routeData.x){ //if our vertex is needed for this route's polyline
			oVert.uv = vec2(clamp(float(vtx)/float(routeData.x),0,1), 0); //set its UV linearly based on how far it is on the line
			newP.xy = texelFetch(uPoints, int(routeData.y + vtx)).xy; //and set its position using the offset and vertex id 
			// newP.z = TDSimplexNoise(newP.xyz * uTurb.z + uTime*uTurb.y) * uTurb.x; //use simplex noise TD fxn
			newP.z = texture(sTurb, newP.xy * 2.0).r * uTurb.x; //use newP.xy as uv lookup coords
			newP.z += TDSimplexNoise(newP.xyz * uTurb.z + uTime*uTurb.y) * uTurb.x * .1; //use simplex noise TD fxn

		} 
		//if we have more vertices than points on route, set all extras to the last point on route and make transparent
		else{
			newP.xy = texelFetch(uPoints, int(routeData.y + routeData.x-1)).xy; //set the point location to the last vertex on the line
			oVert.color *= 0.; //set the color to zero
			oVert.uv = vec2(1, 1); //and the UVs to some default 
		}
		oVert.adsr = routeData.z; // send adsr to fragment shader
		oVert.weight = routeData.w; //send weight to fragment shader
		// #if Weightroutes == 1 //use define statement to tell the compiler when to run/skip this code
		// 	oVert.color *= oVert.weight; //multiply each vertex by that route (i.e. Instance) weight. Most common routes are brigher
		// #endif 
	}
	vec4 worldSpacePos = TDDeform(newP);
	gl_Position = TDWorldToProj(worldSpacePos, uvUnwrapCoord);
	// when we need it. If picking is active we don't need lighting, so
	// this entire block of code will be ommited from the compile.
	// The TD_PICKING_ACTIVE define will be set automatically when
	// picking is active.
#ifndef TD_PICKING_ACTIVE

	int cameraIndex = TDCameraIndex();
	oVert.cameraIndex = cameraIndex;
	oVert.worldSpacePos.xyz = worldSpacePos.xyz;
	oVert.color.a = alpha; //update color transparency
	vec3 worldSpaceNorm = normalize(TDDeformNorm(N));
	oVert.worldSpaceNorm.xyz = worldSpaceNorm;

#else // TD_PICKING_ACTIVE

	// This will automatically write out the nessessary values
	// for this shader to work with picking.
	// See the documentation if you want to write custom values for picking.
	TDWritePickingValues();

#endif // TD_PICKING_ACTIVE
}
