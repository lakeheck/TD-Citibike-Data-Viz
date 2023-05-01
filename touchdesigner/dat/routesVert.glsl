uniform float uAlphaFront;
uniform float uShadowStrength;
uniform vec3 uShadowColor;
uniform vec3 uDiffuseColor;
uniform vec3 uAmbientColor;
uniform vec3 uSpecularColor;
uniform float uShininess;
uniform vec2 uUnrolledTexRes; 



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
	float time;
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
	//idk mod() wasnt working so had to write it out longform...
	// float x = floor(fract(TDInstanceID() / suPosRes.x) * suPosRes.x) ;
	// float y = floor(TDInstanceID() / suPosRes.y);
	// vec2 ref = vec2(x,y) + vec2(0.5); //grab middle of px
	// ref /= suPosRes; //convert to uv

	vec3 uvUnwrapCoord = TDInstanceTexCoord(TDUVUnwrapCoord());

	//sample uv - we need to add so that the points of like geometry stay "together" 
	// newP.xy += texelFetch(sPos, ivec2(int(x), int(y)) , 0).rg;



	//grab num pionts for route from route lookup 
	vec4 routeData = vec4(TDInstanceCustomAttrib0()); // pts in route, start lookup index offset, adsr


	// // This is here to ensure we only execute lighting etc. code
	float alpha = 1.;

	// we want to just skip instances not filled with event data
	if(routeData.x <0){
		newP.xy = vec2(0);
		alpha = 0.0;
	}else
	{
		if(vtx < routeData.x){ 
			// ivec2 lookup = index_to_uv(int(routeData.y) + vtx -1, uUnrolledTexRes);
			// newP.xy = texelFetch(sUnrolledRoutes, lookup, 0).xy;
			// vec2 ref = vec2(lookup) + vec2(0.5);
			// ref /= uUnrolledTexRes;
			// newP.xy = texture(sUnrolledRoutes, ref).xy;
			oVert.uv = vec2(clamp(float(vtx)/float(routeData.x),0,1), 0);
			// newP.xy = uPoints[int(routeData.y + vtx)]; //index with start offset plus vertex number, if our vtx number is less than the number of points on route
			newP.xy = texelFetch(uPoints, int(routeData.y + vtx)).xy;
		} 
		//if we have more vertices than points on route, set all extras to the last point on route and make transparent
		else{
			// ivec2 lookup = index_to_uv(int(routeData.y) + int(routeData.x)-1, uUnrolledTexRes);
			newP.xy = texelFetch(uPoints, int(routeData.y + routeData.x-1)).xy;
			// newP.xy = texelFetch(sUnrolledRoutes, lookup, 0).xy;
			oVert.color *= 0.;
			oVert.uv = vec2(1, 1);
		}
		oVert.adsr = routeData.z;
		oVert.time = routeData.w;
	}


	// newP = vec3(id, vtx, 0);
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
	oVert.color = TDInstanceColor(TDPointColor());
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
